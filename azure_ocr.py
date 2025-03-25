import re
from azure.ai.formrecognizer import DocumentAnalysisClient
from azure.core.credentials import AzureKeyCredential
import pyautogui
import time
import os
from dotenv import load_dotenv


class AzureOCRFormRecognizer:
    def __init__(self, endpoint, key):
        self.client = DocumentAnalysisClient(
            endpoint=endpoint, credential=AzureKeyCredential(key)
        )

    def take_screenshot(self, path="form_screenshot.png"):
        time.sleep(1)
        screenshot = pyautogui.screenshot()
        screenshot.save(path)
        return path

    def is_possible_field_label(self, text):
        keywords = [
            "name",
            "email",
            "password",
            "phone",
            "address",
            "number",
            "confirm",
            "re-enter",
            "account",
            "mobile",
            "username",
        ]
        text = text.lower()
        return (
            any(kw in text for kw in keywords) and len(text) <= 40 and text[0].isalpha()
        )

    def analyze_form(self, image_path):
        with open(image_path, "rb") as f:
            poller = self.client.begin_analyze_document("prebuilt-layout", document=f)
            result = poller.result()
            self.visualize_detected_fields(image_path, result)

        all_text = []
        for page in result.pages:
            for line in page.lines:
                content = line.content.strip()
                if content:
                    all_text.append(content)

        # Filter likely input fields
        input_labels = [t for t in all_text if self.is_possible_field_label(t)]

        user_inputs = {}
        print("\n📝 Detected Input Field Labels:\n")
        for label in input_labels:
            value = input(f"Enter value for '{label}': ")
            user_inputs[label] = value

        return user_inputs

    def visualize_detected_fields(
        self, image_path, result, output_path="highlighted_form.png"
    ):
        from PIL import Image, ImageDraw

        image = Image.open(image_path)
        draw = ImageDraw.Draw(image)

        for page in result.pages:
            for line in page.lines:
                for region in getattr(line, "bounding_regions", []):
                    if region.polygon:
                        try:
                            # Convert normalized coordinates (0–1) to pixel coordinates
                            points = [
                                (pt.x * image.width, pt.y * image.height)
                                for pt in region.polygon
                            ]
                            draw.polygon(points, outline="red", width=2)
                        except Exception as e:
                            print(f"⚠️ Error drawing region: {e}")

        image.save(output_path)
        print(f"✅ Highlighted image saved to {output_path}")


# azure_ocr.py

# if you split it

load_dotenv()

endpoint = "https://jarvisocr222.cognitiveservices.azure.com/"
key = os.getenv("AZURE")

ocr = AzureOCRFormRecognizer(endpoint, key)
screenshot_path = ocr.take_screenshot()
field_data = ocr.analyze_form(screenshot_path)

print("\n✅ Collected Data:")
for k, v in field_data.items():
    print(f"{k}: {v}")
