import json
import os
import psycopg2
from datetime import date, datetime
from google.cloud import vision
from PIL import Image, ImageDraw
import pyautogui
import time
import io
import openai
from selenium import webdriver
from selenium.webdriver.common.by import By
from dateutil import parser as date_parser


class SmartFormFiller:
    def __init__(self, credentials_path=None):
        if credentials_path:
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = credentials_path
        self.vision_client = vision.ImageAnnotatorClient()

    def get_user_id(self, config_path="user_config.json"):
        try:
            with open(config_path, "r") as f:
                data = json.load(f)
                return data.get("user_id")
        except Exception as e:
            print(f"Error reading config: {e}")
            return None

    def get_user_data(self, user_id):
        try:
            db_url = os.getenv("DATABASE_URL")
            conn = psycopg2.connect(db_url)
            cur = conn.cursor()
            cur.execute(
                """
                SELECT first_name, last_name, email, phone, street_name, house_apartment,
                       city, state, zip_code, country, date_of_birth, gender
                FROM users WHERE id = %s
                """,
                (user_id,),
            )
            row = cur.fetchone()
            cur.close()
            conn.close()

            if row:
                columns = [
                    "first_name",
                    "last_name",
                    "email",
                    "phone",
                    "street_name",
                    "house_apartment",
                    "city",
                    "state",
                    "zip_code",
                    "country",
                    "date_of_birth",
                    "gender",
                ]
                user_data = dict(zip(columns, row))

                # Convert date fields to strings
                for key, value in user_data.items():
                    if isinstance(value, (date, datetime)):
                        user_data[key] = value.isoformat()

                # Add full name
                user_data["full_name"] = (
                    f"{user_data.get('first_name', '')} {user_data.get('last_name', '')}".strip()
                )

                return user_data
            else:
                return {}
        except Exception as e:
            print(f"Database error: {e}")
            return {}

    def take_screenshot(self, path="form.png"):
        time.sleep(1)
        screenshot = pyautogui.screenshot()
        screenshot.save(path)
        return path

    def extract_text_annotations(self, image_path):
        with io.open(image_path, "rb") as image_file:
            content = image_file.read()
        image = vision.Image(content=content)
        response = self.vision_client.text_detection(image=image)
        return response.text_annotations

    def highlight_annotations(self, image_path, annotations, output="highlighted.png"):
        img = Image.open(image_path)
        draw = ImageDraw.Draw(img)
        for annotation in annotations[1:]:  # skip full text
            if annotation.bounding_poly:
                vertices = [(v.x, v.y) for v in annotation.bounding_poly.vertices]
                draw.line(vertices + [vertices[0]], fill="red", width=2)
        img.save(output)
        return output

    def ask_openai_what_to_fill(self, field_labels, user_data, api_key):
        openai.api_key = api_key
        prompt = (
            "You are a smart form-filling assistant.\n\n"
            "Given the following detected form field labels:\n"
            f"{field_labels}\n\n"
            "And this user data:\n"
            f"{json.dumps(user_data, indent=2)}\n\n"
            "Your task is to return a JSON object of form fields that can be filled using only the available user data.\n\n"
            "✅ Important Instructions:\n"
            "- ONLY return fields that directly match the provided form labels.\n"
            "- DO NOT infer or hallucinate any fields that are not in the list.\n"
            "- If the form requires 'full name', return it as a combination of first and last name.\n"
            "- If a field contains both first and last name (e.g., 'Name', 'Your Name', etc.), return the full name instead.\n"
            "❌ Never return both 'First name' and 'Full name' or 'Your name' and 'First and last name'. Only the best match.\n"
            "- The key should be the field name in the image and the value from the user data if found"
            "- If Password iss required return in the json Password:empty to let the user know that he has to fill it on his own"
            "- Return a clean JSON (no markdown or explanations).\n\n"
            "🎯 Output Format Example:\n"
            '{\n  "Full Name": "John Doe",\n  "Email": "john@example.com"\n "Password":empty \n}'
        )

        response = openai.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a form autofiller assistant."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
        )
        try:
            import re

            reply = response.choices[0].message.content
            # Extract JSON block even if it's wrapped in ```json ``` using regex
            match = re.search(r"```json\s*(\{.*?\})\s*```", reply, re.DOTALL)
            if match:
                json_str = match.group(1)
            else:
                json_str = reply.strip()  # fallback if no code block

            return json.loads(json_str)
            return json.loads(reply)
        except Exception as e:
            print(f"❌ Error parsing response: {e}\n{response}")
            return {}

    def normalize_url(self, full_url):
        from urllib.parse import urlparse, urlunparse

        """Strip query params and fragments from URL to match known forms."""
        parsed = urlparse(full_url)
        normalized = urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", "", ""))
        return normalized

    def run(self, credentials_path, openai_key):
        url = self.get_active_browser_url()
        url = self.normalize_url(url)
        user_id = self.get_user_id()
        user_data = self.get_user_data(user_id)

        if url == "https://www.amazon.com/gp/buy/addressselect/handlers/display.html":
            print("🛠️ Running pre-automation for Amazon address selection...")
            # 🔼 Scroll up first (in case page is already scrolled down)
            pyautogui.scroll(1000)
            time.sleep(1)

            # 🔁 Refresh the page
            pyautogui.press("f5")
            time.sleep(3)  # Wait for page to reload fully

            pyautogui.click(500, 744)
            time.sleep(0.5)
            pyautogui.write("Israel", interval=0.1)
            time.sleep(0.2)
            pyautogui.press("enter")
            time.sleep(2)  # Wait for page to load
            pyautogui.scroll(-150)  # Scroll down a bit
            time.sleep(1)

        if url:
            print(f"URL IS {url}")
            form_data = self.load_known_form(url)
            if form_data:
                print("🧠 Known form detected. Autofilling using stored coordinates...")
                self.autofill_known_form(form_data, user_data)
                return
        screenshot = self.take_screenshot()
        annotations = self.extract_text_annotations(screenshot)
        field_labels = list(
            {t.description.strip() for t in annotations if t.description.strip()}
        )

        highlighted_path = self.highlight_annotations(screenshot, annotations)
        print(f"📸 Highlighted image saved as {highlighted_path}")

        print("🤖 Asking OpenAI which fields can be filled...")
        field_to_value = self.ask_openai_what_to_fill(
            field_labels, user_data, openai_key
        )

        print("\n✅ Fields to Autofill:")
        for field, value in field_to_value.items():
            print(f"{field}: {value}")

        return field_to_value

    def load_known_form(self, url):
        try:
            with open("known_forms.json", "r") as f:
                all_forms = json.load(f)
            return all_forms.get(url)
        except Exception as e:
            print(f"❌ Error loading known forms: {e}")
            return None

    def autofill_known_form(self, form_data, user_data):
        for label, field in form_data.items():
            key = field["key"]
            x = field["x"]
            y = field["y"]
            value = user_data.get(key)
            if not value:
                print(f"⚠️ Missing value for: {key}")
                continue
            print(f"→ Filling '{label}' with '{value}' at ({x}, {y})")
            # 🖱️ Click the field
            pyautogui.click(x, y)
            time.sleep(0.2)

            # 🧹 Clear existing text
            pyautogui.hotkey("ctrl", "a")  # Select all
            pyautogui.press("backspace")  # Delete
            pyautogui.write(str(value), interval=0.05)
            time.sleep(0.2)

    def get_active_browser_url(self):
        import pyperclip
        import pygetwindow as gw

        try:
            window = gw.getActiveWindow()
            if window and (
                "Chrome" in window.title
                or "Edge" in window.title
                or "Brave" in window.title
            ):
                pyautogui.hotkey("ctrl", "l")  # Focus address bar
                time.sleep(0.1)
                pyautogui.hotkey("ctrl", "c")  # Copy URL
                time.sleep(0.1)
                url = pyperclip.paste()
                print(f"🌐 Current URL: {url}")
                return url
            else:
                print("⚠️ Active window is not a supported browser.")
                return None
        except Exception as e:
            print(f"❌ Failed to get URL: {e}")
            return None

    def create_reminder_from_screen(self, reminder_system, openai_key):
        from google_calendar import add_event_to_calendar

        user_id = self.get_user_id()
        if not user_id:
            print("❌ User ID not found.")
            return

        print("📸 Taking screenshot...")
        screenshot = self.take_screenshot("reminder_screenshot.png")
        annotations = self.extract_text_annotations(screenshot)
        all_text = "\n".join([a.description for a in annotations])

        now = datetime.now()
        formatted_now = now.strftime("%Y-%m-%d %H:%M:%S")

        prompt = f"""
        You are a reminder assistant. The following is extracted from a message/screenshot of a conversation/email/document:
        Below is the full message history:

        --- START MESSAGE ---
        {all_text}
        --- END MESSAGE ---

        Today's date/time: {formatted_now}
        🎯 Your task:
        - Analyze the conversation.
        - Understand which message is the **actual confirmed reminder**.
        - Ignore suggestions or options unless they are agreed upon.

        🧠 Output must be a JSON in this format:
        {{
        "title": "...",           # Summary of the reminder (in the **same language** as the original message)
        "priority": "low/medium/high",
        "datetime": "ISO format like 2025-03-10T16:00:00"
        }}

        ⚠️ VERY IMPORTANT:
        - If the reminder message is in Hebrew, Arabic, or any other language, write the title in **that exact same language**.
        - Do NOT translate the title to English.
        - NEVER include the time inside the title string.
        - If no time is mentioned, assume today at {formatted_now}.
        - If the time mentioned has already passed today, assume it’s for tomorrow.

        Return **only** the JSON output. Do not include explanations or extra text.

        """

        try:
            openai.api_key = openai_key
            response = openai.chat.completions.create(
                model="gpt-4-turbo",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a helpful reminder assistant.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
            )
            content = response.choices[0].message.content.strip()
            print("🔍 GPT-4o response:", content)

            import re

            # Try extracting JSON from within code block
            match = re.search(r"\{.*?\}", content, re.DOTALL)
            if match:
                json_str = match.group(0)
            else:
                json_str = content  # fallback

            try:
                data = json.loads(json_str)
            except json.JSONDecodeError as e:
                print(f"❌ JSON parsing error: {e}")
                return

            dt = date_parser.parse(data["datetime"])
            reminder_system.create_reminder(
                user_id, data["title"], data["priority"], dt.isoformat()
            )

            # 📅 Add to Google Calendar
            user_data = self.get_user_data(user_id)
            email = user_data.get("email")
            if email:
                add_event_to_calendar(
                    email, data["title"], f"Priority: {data['priority']}", dt
                )

        except Exception as e:
            print(f"❌ Failed to create reminder from screen: {e}")

