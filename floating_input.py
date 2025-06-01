from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLineEdit, QPushButton
from PyQt6.QtCore import Qt, QSize, QPoint
import qtawesome as qta

from vision_ocr import SmartFormFiller
from ReminderSystem import ReminderSystem
import os
import threading
from dotenv import load_dotenv
from form_filler_agent import FormFillerAgent
import pyperclip
from urllib.parse import urlparse
import pyautogui
import time

load_dotenv()


class FloatingInputBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.agent = FormFillerAgent(
            "forms_config.json", "user_config.json", headless=False
        )

        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(260, 42)

        self.dragging = False
        self.offset = QPoint()

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(0)  # ❗ No spacing between input and button

        # Input field
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Type a message...")
        self.input_field.setStyleSheet(
            """
            QLineEdit {
                background-color: #1e1e1e;
                color: white;
                border: 2px solid #555;
                border-top-left-radius: 10px;
                border-bottom-left-radius: 10px;
                border-right: none;
                padding: 6px 8px;
                font-size: 13px;
            }
        """
        )
        self.input_field.installEventFilter(self)
        self.setMouseTracking(True)
        self.input_field.setMouseTracking(True)

        # Send button
        self.send_button = QPushButton()
        self.send_button.setIcon(qta.icon("mdi.send", color="white"))
        self.send_button.setFixedSize(45, 30)
        self.send_button.setIconSize(QSize(18, 18))
        self.send_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.send_button.setStyleSheet(
            """
            QPushButton {
                background-color: #1e1e1e;
                border: 2px solid #555;
                border-left: none;
                border-top-right-radius: 10px;
                border-bottom-right-radius: 10px;
            }
            QPushButton:hover {
                background-color: #2c2c2c;
            }
        """
        )
        self.send_button.installEventFilter(self)
        self.send_button.setMouseTracking(True)
        layout.addWidget(self.input_field, stretch=1)
        layout.addWidget(self.send_button)

        self.hide()
        self.filler = SmartFormFiller("jarvis-ocr.json")
        self.reminder_system = ReminderSystem()
        self.openai_key = os.getenv("OPENAI_API_KEY")

    # Make draggable
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragging = True
            self.offset = event.globalPosition().toPoint() - self.pos()

    def mouseMoveEvent(self, event):
        if self.dragging:
            self.move(event.globalPosition().toPoint() - self.offset)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragging = False

    def eventFilter(self, source, event):
        if (
            event.type() == event.Type.MouseButtonPress
            and event.button() == Qt.MouseButton.LeftButton
        ):
            self.mousePressEvent(event)
        elif event.type() == event.Type.MouseMove and self.dragging:
            self.mouseMoveEvent(event)
        elif (
            event.type() == event.Type.MouseButtonRelease
            and event.button() == Qt.MouseButton.LeftButton
        ):
            self.mouseReleaseEvent(event)
        return super().eventFilter(source, event)

    def handle_send_input(self):

        text = self.input_field.text().strip()
        parts = text.split(maxsplit=1)
        cmd = parts[0].lower()
        if text == "create reminder":
            print("🧠 Triggering reminder from screen...")
            # filler = SmartFormFiller("jarvis-ocr.json")
            # reminder_system = ReminderSystem()
            # openai_key = os.getenv("OPENAI_API_KEY")
            threading.Thread(
                target=self.filler.create_reminder_from_screen,
                args=(self.reminder_system, self.openai_key),
                daemon=True,
            ).start()
            self.input_field.clear()
            self.hide()
        elif cmd == "register":
            # 1) extract password if given
            if len(parts) == 2:
                pwd = parts[1]
            else:
                print("❗ Usage: register <password>")
                return

            # 2) grab URL from active browser:
            #    - focus address bar
            import pygetwindow as gw

            browser_win = None
            for name in ("Chrome", "Edge", "Firefox"):
                wins = gw.getWindowsWithTitle(name)
                if wins:
                    browser_win = wins[0]
                    break

            if not browser_win:
                print("❌ Couldn't find a browser window.")
                return

            browser_win.activate()  # bring to front
            time.sleep(0.3)  # let the OS switch focus
            pyautogui.hotkey("ctrl", "l")
            time.sleep(0.1)
            pyautogui.hotkey("ctrl", "c")
            time.sleep(0.1)
            start_url = pyperclip.paste().strip()

            if not start_url or not start_url.startswith("http"):
                print("❌ Could not read URL from browser.")
                return

            # 3) figure out site_key
            domain = urlparse(start_url).netloc.lower().lstrip("www.")
            site_key = None
            for key, cfg in self.agent.forms_config.items():
                cfg_dom = urlparse(cfg["url"]).netloc.lower().lstrip("www.")
                if domain.endswith(cfg_dom):
                    site_key = key
                    break

            if not site_key:
                print(f"❌ No form config for {domain}")
                site_key = f"auto_{domain}"
                print(f"ℹ️  No curated config for {domain}; will attempt auto-mapping.")
                # return

            # 4) inject password into agent.user_data
            self.agent.user_data["password"] = pwd
            self.agent.user_data["password_check"] = pwd

            # 5) launch form fill
            print(f"🧠 Filling form on {site_key}…")
            threading.Thread(
                target=self.agent.fill_form,
                args=(site_key, print, start_url),
                daemon=True,
            ).start()

            self.input_field.clear()
            self.hide()
            return
        elif text:
            print(f"📤 Input sent: {text}")
            self.input_field.clear()
            self.hide()
