import os
import base64
from openai import OpenAI
from dotenv import load_dotenv


def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")


def process_images_in_directory(images_dir):
    client = OpenAI()

    for filename in os.listdir(images_dir):
        if filename.lower().endswith((".jpg")):
            image_path = os.path.join(images_dir, filename)

            # Getting the base64 string
            base64_image = encode_image(image_path)

            response = client.chat.completions.create(
                model="gpt-4o-mini",
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
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_image}"
                                },
                            },
                        ],
                    }
                ],
            )

            print(response.choices[0].message.content)


def main():
    load_dotenv()
    images_directory = "./images"
    process_images_in_directory(images_directory)


if __name__ == "__main__":
    main()
