# RemindersSystem.py
import openai
import speech_recognition as sr
from dateutil import parser as date_parser  # to parse dates from strings
import psycopg2
import uuid
from datetime import datetime, timedelta
from dotenv import load_dotenv
import subprocess
import time
import threading
from multiprocessing import Process

# from popup_launcher import launch_reminder_popup

load_dotenv()

DATABASE_URL = "postgresql://postgres:Jarvisgroup15@db.nsgeslmkrejtlifazhnu.supabase.co:5432/postgres"
DATABASE_URL = "postgresql://postgres.nsgeslmkrejtlifazhnu:Jarvisgroup15@aws-0-eu-central-1.pooler.supabase.com:6543/postgres"


class ReminderSystem:
    def __init__(self, db_url=DATABASE_URL):
        self.db_url = db_url

    def create_reminder(self, user_id, title, priority, datetime_str, google_event_id):
        try:
            conn = psycopg2.connect(self.db_url)
            cursor = conn.cursor()

            reminder_id = str(uuid.uuid4())
            reminder_time = datetime.fromisoformat(datetime_str)

            cursor.execute(
                """
                INSERT INTO reminders (id, user_id, title, priority, datetime, google_event_id)
                VALUES (%s, %s, %s, %s, %s, %s)
            """,
                (reminder_id, user_id, title, priority, reminder_time, google_event_id),
            )

            conn.commit()
            print(f"Reminder '{title}' created successfully.")
        except Exception as e:
            print(f"Error creating reminder: {e}")
        finally:
            if conn:
                cursor.close()
                conn.close()

    def delete_reminder(self, reminder_id):
        try:
            conn = psycopg2.connect(self.db_url)
            cursor = conn.cursor()
            cursor.execute(
                "SELECT google_event_id, user_id FROM reminders WHERE id=%s",
                (reminder_id,),
            )
            event_id, user_id = cursor.fetchone()
            cursor.execute("DELETE FROM reminders WHERE id = %s", (reminder_id,))
            conn.commit()
            print("Reminder deleted.")
            if event_id:
                user_mail = self.get_user_data(user_id)["email"]
                from google_calendar import delete_event

                delete_event(user_mail, event_id)
        except Exception as e:
            print(f"Error deleting reminder: {e}")

        finally:
            if conn:
                cursor.close()
                conn.close()

    def get_upcoming_reminders(self, user_id):
        try:
            conn = psycopg2.connect(self.db_url)
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, title, priority, datetime FROM reminders
                WHERE user_id = %s AND completed = FALSE
                ORDER BY datetime ASC
            """,
                (user_id,),
            )
            return cursor.fetchall()
        except Exception as e:
            print(f"Error fetching reminders: {e}")
            return []
        finally:
            if conn:
                cursor.close()
                conn.close()

    def get_user_data(self, user_id):
        try:
            import os

            db_url = os.getenv("DATABASE_URL")
            conn = psycopg2.connect(db_url)
            cur = conn.cursor()
            cur.execute(
                "SELECT first_name,email, city, country FROM users WHERE id = %s",
                (user_id,),
            )
            result = cur.fetchone()
            cur.close()
            conn.close()
            if result:
                first_name, email, city, country = result
                return {
                    "name": first_name,
                    "email": email,
                    "city": city,
                    "country": country,
                }
            else:
                return {}
        except Exception as e:
            print(f"Database error: {e}")
            return {}

    def create_reminder_from_voice(self, user_id):
        recognizer = sr.Recognizer()
        from google_calendar import add_event_to_calendar

        # from main_window import get_user_data

        with sr.Microphone() as source:
            print("Listening for a reminder command...")
            recognizer.adjust_for_ambient_noise(source)
            audio = recognizer.listen(source)

        try:
            command = recognizer.recognize_google(audio)
            print(f"Recognized command: {command}")
        except sr.UnknownValueError:
            print("Sorry, I couldn't understand that.")
            return
        except sr.RequestError as e:
            print(f"Speech recognition error: {e}")
            return
        now = datetime.now()
        formatted_now = now.strftime("%Y-%m-%d %H:%M:%S")

        # Prompt for OpenAI
        prompt = f"""
        Extract the reminder details from this command: "{command}"

        Respond in JSON format with:
        {{
            "title": "...",
            "priority": "low/medium/high",
            "datetime": "ISO format (like 2025-03-10T16:00:00)"
        }}
        Today's current datetime is: {formatted_now}
        If the date is not mentioned, assume the user means today.
        If the time has already passed today, assume the user meant tomorrow.
        If any other new date in the future create it.
        If priority is not mentioned, assume "medium".
        
        """

        try:
            response = openai.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.4,
            )
            content = response.choices[0].message.content.strip()
            print(f"GPT response:\n{content}")

            import json

            data = json.loads(content)

            # Validate and create reminder
            title = data["title"]
            priority = data.get("priority", "medium").lower()
            dt = date_parser.parse(data["datetime"])  # safe ISO parsing
            # Fix if the parsed datetime is in the past or has a wrong year
            now = datetime.now()
            if dt.year < now.year:
                dt = dt.replace(year=now.year)

            # If datetime is still in the past (like today at 9am but it's already 10am)
            if dt < now:
                dt += timedelta(days=1)  # Pus
            user_data = self.get_user_data(user_id)
            email = user_data.get("email")
            add_event_to_calendar(email, title, f"Priority: {priority}", dt)
            self.create_reminder(user_id, title, priority, dt.isoformat())

        except Exception as e:
            print(f"Failed to create reminder from voice: {e}")

    from datetime import timedelta

    def snooze_reminder(self, reminder_id, minutes=10):
        try:
            conn = psycopg2.connect(self.db_url)
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE reminders
                SET datetime = datetime + INTERVAL '%s minutes', snoozed = TRUE
                WHERE id = %s
            """,
                (minutes, reminder_id),
            )
            conn.commit()
            print(f"Reminder snoozed for {minutes} minutes.")
        except Exception as e:
            print(f"Error snoozing reminder: {e}")
        finally:
            if conn:
                cursor.close()
                conn.close()

    def start_reminder_checker(self, user_id):
        def check_loop():
            from popup_launcher import launch_reminder_popup  # 👈 avoid circular import
            from datetime import timedelta

            while True:
                upcoming = self.get_upcoming_reminders(user_id)
                now = datetime.now()

                for reminder in upcoming:
                    reminder_id, title, priority, remind_time = reminder
                    if now <= remind_time <= now + timedelta(minutes=10):
                        print(f"Triggering reminder popup for: {title}")
                        Process(
                            target=launch_reminder_popup, args=(str(reminder_id),)
                        ).start()
                        time.sleep(60)  # prevent multiple popups

                time.sleep(60)

        threading.Thread(
            target=check_loop, daemon=True
        ).start()  # ✅ Start in background

    def get_reminder_by_id(self, reminder_id):
        try:
            conn = psycopg2.connect(self.db_url)
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, title, priority, datetime, snoozed, completed, created_at
                FROM reminders
                WHERE id = %s
            """,
                (reminder_id,),
            )
            return cursor.fetchone()
        except Exception as e:
            print(f"Error fetching reminder: {e}")
            return None
        finally:
            if conn:
                cursor.close()
                conn.close()

    def mark_as_completed(self, reminder_id):
        try:
            conn = psycopg2.connect(self.db_url)
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE reminders SET completed = TRUE WHERE id = %s", (reminder_id,)
            )
            conn.commit()
            print(f"Reminder {reminder_id} marked as completed.")
        except Exception as e:
            print(f"Error marking as completed: {e}")
        finally:
            if conn:
                cursor.close()
                conn.close()

    def update_reminder(self, reminder_id, new_title, new_priority, new_datetime):
        try:
            conn = psycopg2.connect(self.db_url)
            cursor = conn.cursor()

            cursor.execute(
                "SELECT google_event_id, user_id FROM reminders WHERE id=%s",
                (reminder_id,),
            )
            event_id, user_id = cursor.fetchone()

            cursor.execute(
                """
                UPDATE reminders
                SET title = %s, priority = %s, datetime = %s
                WHERE id = %s
            """,
                (new_title, new_priority, new_datetime, reminder_id),
            )
            conn.commit()
            print(f"Reminder {reminder_id} updated.")
            if event_id:  # silent no-op for old rows
                user_mail = self.get_user_data(user_id)["email"]
                from google_calendar import patch_event

                patch_event(
                    user_mail,
                    event_id,
                    new_title,
                    f"Priority: {new_priority}",
                    new_datetime,
                )
        finally:
            if conn:
                cursor.close()
                conn.close()


# reminder_system = ReminderSystem()

# # Example call
# user_id = "62ca6e81-43b9-4a5a-a7f1-f2da9f126f0f"
# reminder_system.create_reminder_from_voice(user_id)
# reminder_system.start_reminder_checker(user_id)
