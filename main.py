import asyncio
import base64
import json
import os
from datetime import datetime
from textwrap import dedent

import logfire
import polars as pl
import structlog
from dotenv import load_dotenv
from openai import AsyncOpenAI
from pydantic import BaseModel


async def main():
    load_dotenv(override=True)
    log = structlog.get_logger()

    # Configure Logfire
    logfire.configure()
    logfire.instrument_openai()

    image_paths = find_image_paths()
    log.info("Found images to process", count=len(image_paths))

    current_time = datetime.now().strftime("%Y%m%d_%H%M")
    output_csv_name = f"outputs/output_{current_time}.csv"
    progress_file = f"outputs/progress_{current_time}.json"
    
    # Initialize progress tracking
    processed_images = load_progress(progress_file)
    remaining_images = [path for path in image_paths if path not in processed_images]
    
    log.info("Progress loaded", 
             total_images=len(image_paths),
             already_processed=len(processed_images),
             remaining=len(remaining_images))

    if not remaining_images:
        log.info("All images already processed!")
        return

    # Initialize CSV file with headers if it doesn't exist
    initialize_csv(output_csv_name)

    # Create async client and semaphore for rate limiting
    client = AsyncOpenAI()
    semaphore = asyncio.Semaphore(5)  # Limit to 5 concurrent requests
    
    # Process images concurrently
    tasks = [
        process_image_with_progress(
            client, image_path, output_csv_name, progress_file, semaphore, log
        )
        for image_path in remaining_images
    ]
    
    log.info("Starting concurrent processing", concurrent_limit=5)
    
    # Process all tasks and handle any exceptions
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Count successes and failures
    successes = sum(1 for r in results if not isinstance(r, Exception))
    failures = sum(1 for r in results if isinstance(r, Exception))
    
    log.info("Processing completed", 
             successes=successes, 
             failures=failures,
             output_file=output_csv_name)


def load_progress(progress_file):
    """Load list of already processed images from progress file."""
    if os.path.exists(progress_file):
        with open(progress_file, 'r') as f:
            return set(json.load(f))
    return set()


def save_progress(progress_file, processed_image):
    """Add a processed image to the progress file."""
    processed_images = load_progress(progress_file)
    processed_images.add(processed_image)
    
    with open(progress_file, 'w') as f:
        json.dump(list(processed_images), f)


def initialize_csv(output_csv_name):
    """Initialize CSV file with headers if it doesn't exist."""
    if not os.path.exists(output_csv_name):
        template_csv = "outputs/output.template.csv"
        df_template = pl.read_csv(template_csv)
        df_template.write_csv(output_csv_name)


def append_to_csv(output_csv_name, intake_forms):
    """Append intake forms to CSV file."""
    rows = []
    for intake_form in intake_forms.list_of_intake_forms:
        rows.append({
            "id_number": intake_form.id_number,
            "species": intake_form.species,
            "condition": intake_form.condition,
            "intake_date": intake_form.intake_date,
            "rescuer_name": f"{intake_form.rescuer_name}                         {intake_form.rescuer_city}",
            "county_found": intake_form.county_found,
            "final_disposition": intake_form.final_disposition,
            "county_released": intake_form.county_released,
            "disposition_date": intake_form.disposition_date,
        })
    
    if rows:
        df_new = pl.DataFrame(rows)
        
        # Read existing CSV and append new data
        df_existing = pl.read_csv(output_csv_name)
        df_combined = df_existing.vstack(df_new)
        df_combined.write_csv(output_csv_name)


async def process_image_with_progress(client, image_path, output_csv_name, progress_file, semaphore, log):
    """Process a single image with progress tracking and immediate CSV writing."""
    async with semaphore:  # Limit concurrent requests
        try:
            log.info("Processing image", image_path=image_path)
            
            with logfire.span('Processing intake form image', image_path=image_path):
                intake_forms = await process_image_async(client, image_path)
                logfire.info("Received result", result=intake_forms.model_dump())
            
            # Immediately append to CSV
            append_to_csv(output_csv_name, intake_forms)
            
            # Save progress
            save_progress(progress_file, image_path)
            
            log.info("Completed processing image", image_path=image_path)
            return True
            
        except Exception as e:
            log.error("Failed to process image", image_path=image_path, error=str(e))
            return False


def find_image_paths():
    images_directory = "inputs/images"

    image_filenames = [
        filename
        for filename in os.listdir(images_directory)
        if filename.lower().endswith((".jpg"))
    ]

    image_paths = [
        os.path.join(images_directory, filename) for filename in image_filenames
    ]

    image_paths.sort(key=lambda p: os.path.basename(p))

    return image_paths


def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")


class IntakeForm(BaseModel):
    id_number: str
    species: str
    condition: str
    intake_date: str
    rescuer_name: str | None
    rescuer_city: str | None
    county_found: str | None
    final_disposition: str | None
    county_released: str | None
    disposition_date: str | None


class IntakeForms(BaseModel):
    list_of_intake_forms: list[IntakeForm]


async def process_image_async(
    client: AsyncOpenAI,
    image_path: str,
) -> IntakeForms:
    model = os.getenv("OPENAI_MODEL")
    year = os.getenv("YEAR")
    base64_image = encode_image(image_path)

    # Get a list of conditions and species from the previous years' reports
    df = pl.read_csv("inputs/previous_years_reports/DNR-2020.csv")
    conditions = df["Condition"].unique().to_list()
    species = df["Species"].unique().to_list()

    system_prompt = dedent(
        f"""
        You are a helpful assistant who is helping a user to extract data from pictures of intake forms.

        Each intake form image could apply to just one ID or multiple IDs.
        In the case of multiple IDs, return an entry for each, with the same data if differences aren't specified.
        The ID numbers MUST range from 1 to 2000, alternately written as {year}-0001 to {year}-2000.
        For example, if you see an ID of 081-084, you should return a list of IntakeForm objects with IDs of {year}-0081, {year}-0082, {year}-0083, and {year}-0084.

        Additional notes:
          - CAGO is an abbreviation for Canada Goose
          - GHOW is an abbreviation for Great Horned Owl
          - RTH is an abbreviation for Red-Tailed Hawk
          - If the species is just "duck", use "Mallard" instead
          - You MUST return dates in the format MM.DD.YY, like 11.30.{year}
          - You MUST abbreviate Indianapolis as Indpls
          - You MUST write Indy as Indpls
          - If the final_disposition is "D" or "E", then the county_released MUST be "N/A"
          - The final_disposition MUST be one of the following: D, R, E, DOA, T, or P
          - The counties MUST all be counties from the state of Indiana
          - The city MUST be a city from the state of Indiana
          - The id_number MUST be between {year}-0001 and {year}-2000
          - On the form, county_found is written as "Co Found"
          - On the form, county_released is written as "Co Rel"
          - On the form, final_disposition is written as "Final Disp"
          - On the form, disposition_date is written as "DT"
          - All of the dates should be for 20{year}, written as {year} in the format MM.DD.YY
          - If the rescuer name doesn't have a last name, use NoLastName
          - If the condition is spread over multiple lines, join phrases with a comma where it makes sense, instead of using a hyphen
          - If the condition is something like "gosling" or "duckling", then make the condition "orphan"
          - If the city is Indianapolis, but no county is listed, then make a best guess at the county based on the city or other location notes
          - If the county found is something like "Brown Co", then make the county found just "Brown"
          - If the county is "unk", then make the county found "Unknown", but if it's blank, just leave it blank
          - For the rescuer name, enter just the main person's name, and not "+ 2 others" or any extra information
          - If the species is hatchling, then change it to Songbird

        Refer to a list of conditions from previous years' report and follow the style of the condition notes:
        {conditions}

        The species SHOULD be one of the following:
        {species}

        Thank you so much for your help!
        """
    )

    response = await client.responses.parse(
        model=model,
        input=[
            {
                "role": "system",
                "content": system_prompt,
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "What is in this image?",
                    },
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"},
                    },
                ],
            },
        ],
        text_format=IntakeForms,
    )

    return response.output_parsed


if __name__ == "__main__":
    asyncio.run(main())
