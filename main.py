import base64
import glob
import os
import pprint
from textwrap import dedent

import openlit
import structlog
from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel


def main():
    log = structlog.get_logger()
    load_dotenv()
    openlit.init()

    images_directory = "inputs/images"

    image_filenames = [
        filename
        for filename in os.listdir(images_directory)
        if filename.lower().endswith((".jpg"))
    ]

    image_paths = [
        os.path.join(images_directory, filename) for filename in image_filenames
    ]

    log.info("Found images to process", count=len(image_paths))

    client = OpenAI()

    for image_path in image_paths:
        log.info("Processing image", image_path=image_path)
        result: IntakeForms = process_image(client, image_path)
        log.info("Received result", result=pprint.pformat(result.model_dump()))


def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")


def load_csv_into_string(csv_path):
    with open(csv_path, "r") as csv_file:
        return csv_file.read()


class IntakeForm(BaseModel):
    id_number: str
    species: str
    condition: str
    intake_date: str
    rescuer_name: str | None
    county_found: str | None
    final_disposition: str | None
    county_released: str | None
    disposition_date: str | None


class IntakeForms(BaseModel):
    list_of_intake_forms: list[IntakeForm]


def process_image(
    client: OpenAI,
    image_path: str,
) -> IntakeForms:
    model = os.getenv("OPENAI_MODEL")
    base64_image = encode_image(image_path)
    previous_reports_path = "inputs/previous_years_reports"

    string_of_csvs = ""
    for csv_file in glob.glob(f"{previous_reports_path}/*.csv"):
        string_of_csvs += f"{csv_file}:\n"
        string_of_csvs += load_csv_into_string(csv_file) + "\n"

    system_prompt = dedent(
        f"""
        You are a helpful assistant who is helping a user to extract data from pictures of intake forms.

        Each intake form image could apply to just one ID or multiple IDs.
        In the case of multiple IDs, return an entry for each, with the same data if differences aren't specified.
        The ID numbers should range from 1 to 2000, alternately written as 24-0001 to 24-2000.
        For example, if you see an ID of 081-084, you should return a list of IntakeForm objects with IDs of 24-0081, 24-0082, 24-0083, and 24-0084.

        CAGO is an abbreviation for Canada Goose.
        Return dates in the format MM.DD.YY, like 11.30.24.

        You should refer to the previous years' reports to know what format to return the data in:
        {string_of_csvs}
        """
    )

    completion = client.beta.chat.completions.parse(
        model=model,
        messages=[
            {
                "role": "system",
                "content": [
                    {
                        "type": "text",
                        "text": system_prompt,
                    }
                ],
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
        response_format=IntakeForms,
    )

    return completion.choices[0].message.parsed


def append_to_output_csv(intake_forms: IntakeForms):
    with open("output.csv", "a") as output_csv:
        for intake_form in intake_forms.list_of_intake_forms:
            output_csv.write(
                f"{intake_form.id_number},{intake_form.species},{intake_form.condition},{intake_form.intake_date},{intake_form.rescuer_name},{intake_form.county_found},{intake_form.final_disposition},{intake_form.county_released},{intake_form.disposition_date}\n"
            )


if __name__ == "__main__":
    main()
