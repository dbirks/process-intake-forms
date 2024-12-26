import os
import base64
from openai import OpenAI
from dotenv import load_dotenv
import structlog


def main():
    log = structlog.get_logger()
    load_dotenv()

    images_directory = "./images"
    # process_images_in_directory(images_directory)

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


def process_image(
    client: OpenAI,
    image_path: str,
):
    model = "gpt-4o"
    base64_image = encode_image(image_path)

    response = client.chat.completions.create(
        model=model,
        messages=[
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
