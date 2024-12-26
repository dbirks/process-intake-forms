import os
import base64
import openai
from dotenv import load_dotenv


def process_images_in_directory(images_dir):
    for filename in os.listdir(images_dir):
        if filename.lower().endswith((".jpg")):
            image_path = os.path.join(images_dir, filename)
            with open(image_path, "rb") as img_file:
                image_data = base64.b64encode(img_file.read()).decode("utf-8")

            response = openai.ChatCompletion.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": "You are an AI that extracts important details from form images.",
                    },
                    {
                        "role": "user",
                        "content": f"Here is an image in base64: {image_data}\nIdentify all important details in this form.",
                    },
                ],
            )
            print(
                f"Result for {filename}:\n",
                response["choices"][0]["message"]["content"],
                "\n",
            )


def main():
    load_dotenv()
    images_directory = "./images"
    process_images_in_directory(images_directory)


if __name__ == "__main__":
    main()
