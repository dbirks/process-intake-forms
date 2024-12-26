import base64
import glob
import os
import string
from textwrap import dedent

import openlit
import structlog
from dotenv import load_dotenv
from openai import OpenAI


def main():
    log = structlog.get_logger()
    load_dotenv(override=True)
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
        result = process_image(client, image_path)
        log.info("Result", result=result)


def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")


def load_csv_into_string(csv_path):
    with open(csv_path, "r") as csv_file:
        return csv_file.read()


def process_image(
    client: OpenAI,
    image_path: str,
):
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

        You have the following reports in CSV format from previous years to use as a reference:
        {string_of_csvs}

        """
    )

    response = client.chat.completions.create(
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
            }
        ],
    )

    return response.choices[0].message.content


if __name__ == "__main__":
    main()
