import threading
import time
from datetime import datetime
from PyQt6.QtCore import QObject, pyqtSignal
from multiprocessing import Process
from popup_process import launch_popup
import random

BREAK_MESSAGES = [
    "💧 Time to hydrate! Go grab a glass of water.",
    "🧘‍♂️ Take a deep breath and stretch your body.",
    "👀 Rest your eyes for a minute — blink and look away from the screen.",
    "🚶‍♀️ Stand up and take a short walk, even just around the room.",
    "☕️ Time for a quick refresh. Get some tea or coffee if you like.",
]


class StudyMode(QObject):
    request_file_summary = pyqtSignal()  # ✅ New signal to notify main thread

    def __init__(self, reminder_system, user_id, parent=None):
        super().__init__()
        self.snoozed_reminders = set()
        self.reminder_system = reminder_system
        self.user_id = user_id
        self.is_active = False
        self.break_interval = 40 * 60  # can be set back to 45 * 60
        self.summary_interval = 40 * 60  # can be set back to 30 * 60
        self._thread = None
        self.parent = parent
        self.break_message_pool = BREAK_MESSAGES.copy()
        random.shuffle(self.break_message_pool)

    def activate(self):
        print("🎓 Study Mode Activated")
        self.is_active = True
        self.snooze_low_priority_reminders()
        self._thread = threading.Thread(target=self.run, daemon=True)
        self._thread.start()

    def deactivate(self):
        print("🛑 Study Mode Deactivated")
        self.is_active = False

    def snooze_low_priority_reminders(self):
        from datetime import datetime, timedelta

        reminders = self.reminder_system.get_upcoming_reminders(self.user_id)
        now = datetime.now()

        for reminder in reminders:
            reminder_id, title, priority, remind_time = reminder
            time_until_reminder = remind_time - now

            # Only snooze if:
            # - Priority is low
            # - Not already snoozed
            # - The reminder is within the next 10 minutes
            if (
                priority == "low"
                and reminder_id not in self.snoozed_reminders
                and timedelta(minutes=0) < time_until_reminder <= timedelta(minutes=10)
            ):
                self.reminder_system.snooze_reminder(reminder_id, minutes=5)
                self.snoozed_reminders.add(reminder_id)
                print(f"🔁 Snoozed low-priority reminder '{title}' by 5 minutes.")

    def run(self):
        from datetime import timedelta

        last_break = datetime.now()
        last_summary = datetime.now()
        last_snooze_check = datetime.now()

        while self.is_active:
            now = datetime.now()

            # 🧠 Check for nearby low-priority reminders every 5 minutes
            if (now - last_snooze_check).seconds > 300:  # every 5 minutes
                self.snooze_low_priority_reminders()
                last_snooze_check = now

            if (now - last_break).seconds > self.break_interval:
                self.show_break_popup()
                last_break = now

            if (now - last_summary).seconds > self.summary_interval:
                print("📁 Checking for open files to suggest summary...")
                self.request_file_summary.emit()
                last_summary = now

            time.sleep(60)

    def show_break_popup(self):
        # Cycle break messages without repeating
        if not self.break_message_pool:
            self.break_message_pool = BREAK_MESSAGES.copy()
            random.shuffle(self.break_message_pool)

        message = self.break_message_pool.pop()

        print("💡 Break Reminder:", message)
        p = Process(target=launch_popup, args=(message,))
        p.start()
