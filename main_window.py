from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QLabel,
    QPushButton,
    QStackedWidget,
    QHBoxLayout,
    QTextEdit,
    QFileDialog,
    QMessageBox,
    QToolTip,
    QFrame,
    QInputDialog,
    QDialog,
    QFormLayout,
    QDateTimeEdit,
    QComboBox,
    QScrollArea,
    QSizePolicy,
)
from PyQt6.QtCore import Qt, QPropertyAnimation, QRect, QDateTime, QTimer
from context_automation import ContextBasedAutomation
import keyboard
import time
import qtawesome as qta
import openai
from PyPDF2 import PdfReader
from docx import Document
from dotenv import load_dotenv
from PyQt6.QtCore import QThread, pyqtSignal
from AppManager import ListAppsDialog
from ReminderSystem import ReminderSystem
from PyQt6.QtWidgets import QListWidget, QListWidgetItem, QLineEdit, QTextEdit
import datetime
from dateutil import parser as date_parser
import psycopg2
import os
import json
from activity_GUI import DashboardPanel  # Assuming this is your DashboardPanel file
from study_mode import StudyMode


load_dotenv()

import mimetypes


class ReminderLoaderWorker(QThread):
    finished = pyqtSignal(list)  # Emits loaded reminders

    def __init__(self, reminder_system, user_id):
        super().__init__()
        self.reminder_system = reminder_system
        self.user_id = user_id

    def run(self):
        reminders = self.reminder_system.get_upcoming_reminders(self.user_id)
        self.finished.emit(reminders)


class ScreenTimeLoader(QThread):
    finished = pyqtSignal(QWidget)

    def __init__(self, tracker_instance, parent=None):
        super().__init__(parent)
        self.tracker_instance = tracker_instance

    def run(self):
        from global_tracker import tracker_instance

        activity_data = self.tracker_instance.get_activity_data()
        dashboard = DashboardPanel(activity_data, self.tracker_instance)
        self.finished.emit(dashboard)


class SummarizeFileWorker(QThread):
    finished = pyqtSignal(str)  # Signal to emit the result (new file name)
    error = pyqtSignal(str)  # Signal to emit error messages

    def __init__(self, file_path, file_content, parent=None):
        super().__init__(parent)
        self.file_path = file_path
        self.file_content = file_content

    def run(self):
        try:
            prompt = f"""
            You are provided with the content of a file: {self.file_content}.
            Your task is to suggest a meaningful and detailed summary for the file based on its primary topic and context.

            If the content is in English:
            - The summary must be in English and properly written.

            If the content is in Hebrew:
            - The summary must be in Hebrew, properly written.
            """

            # API call to OpenAI
            response = openai.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                # max_tokens=500,
                temperature=0.4,
            )
            summary = response.choices[0].message.content.strip()

            self.finished.emit(summary)  # Emit the result
        except Exception as e:
            self.error.emit(str(e))  # Emit any error


class RenameFileWorker(QThread):
    finished = pyqtSignal(str)  # Signal to emit the result (new file name)
    error = pyqtSignal(str)  # Signal to emit error messages

    def __init__(self, file_path, file_content, parent=None):
        super().__init__(parent)
        self.file_path = file_path
        self.file_content = file_content

    def run(self):
        try:
            prompt = f"""
            You are provided with the content of a file: {self.file_content}.
            Your task is to suggest a meaningful and concise name for the file based on its primary topic and context. The name must:
            - Be 1-4 words maximum.
            - Clearly describe the main subject or theme of the file.
            - Reflect the specific context or domain, such as "ContractDraft - The main subject in the file " for a legal document, "SalesReport" for financial content, or "ResearchSummary" for academic material.
            - Add to it the context of the file.
            - Avoid generic or vague terms like "Document," "File," or "Notes."
            - Don't include numbers in the name.

            If the content is in English:
            - The name must be in English and properly capitalized, e.g., "ProjectPlan" or "BudgetReport."

            If the content is in Hebrew:
            - The name must be in Hebrew, properly spaced and meaningful, e.g., "הנושא של המסמך - חוזה משפטי" for a legal document or "דו\"ח כספי" for financial content.

            Examples:
            - For legal content in English: "ContractTerms" or "CourtRuling."
            - For financial content in Hebrew: "דו\"ח הכנסות" or "סיכום חודשי."
            - For legal content in Hebrew:  "פסק דין - שם הנושא של המסך" etc.
            - For academic content in English: "PhysicsNotes" or "ThesisOutline."

            Please provide a precise and meaningful name for the file based on the content provided, in the appropriate language.
            """

            # API call to OpenAI
            response = openai.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=40,
                temperature=0.4,
            )
            new_name = response.choices[0].message.content.strip()

            # Sanitize the name
            import re

            sanitized_name = re.sub(r"[^\w\s-]", "", new_name).strip()
            self.finished.emit(sanitized_name)  # Emit the result
        except Exception as e:
            self.error.emit(str(e))  # Emit any error


class HoverLabel(QLabel):
    def __init__(self, text, description, parent=None):
        super().__init__(parent)

        # Set Material Design icon for info
        self.icon = qta.icon("mdi.information", color="white")
        self.default_text = ""
        self.description = description
        self.tooltip_box = QLabel(self)
        self.tooltip_box.setText(self.description)
        self.tooltip_box.setStyleSheet(
            """
            background-color: #222;
            color: #fff;
            border: 1px solid #555;
            padding: 5px;
            border-radius: 5px;
            font-size: 12px;
        """
        )
        self.tooltip_box.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.tooltip_box.setWindowFlags(Qt.WindowType.ToolTip)
        self.tooltip_box.hide()

        # Set the icon as the default QLabel content
        self.setPixmap(self.icon.pixmap(24, 24))  # Icon size
        self.setStyleSheet("background: transparent;")

    def enterEvent(self, event):
        """Show tooltip box on hover."""
        self.tooltip_box.move(self.mapToGlobal(self.rect().bottomLeft()))
        self.tooltip_box.show()
        super().enterEvent(event)

    def leaveEvent(self, event):
        """Hide tooltip box when hover ends."""
        self.tooltip_box.hide()
        super().leaveEvent(event)


from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, QRectF, QPropertyAnimation, pyqtProperty
from PyQt6.QtGui import QPainter, QColor, QBrush


class AnimatedToggle(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(60, 30)
        self._position = 2
        self._checked = False
        self._animation = QPropertyAnimation(self, b"position", self)
        self._animation.setDuration(200)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def mousePressEvent(self, event):
        self._checked = not self._checked
        self.animate()
        self.clicked.emit(self._checked)

    def animate(self):
        end_pos = self.width() - 28 if self._checked else 2
        self._animation.stop()
        self._animation.setEndValue(end_pos)
        self._animation.start()

    def isChecked(self):
        return self._checked

    def setChecked(self, state):
        self._checked = state
        self._position = self.width() - 28 if state else 2
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Background
        bg_color = QColor("#4CAF50") if self._checked else QColor("#f44336")
        painter.setBrush(QBrush(bg_color))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(self.rect(), 15, 15)

        # Handle
        painter.setBrush(QBrush(QColor("#FFF")))
        painter.drawEllipse(QRectF(self._position, 2, 26, 26))

    def get_position(self):
        return self._position

    def set_position(self, pos):
        self._position = pos
        self.update()

    position = pyqtProperty(float, fget=get_position, fset=set_position)

    # Custom signal
    from PyQt6.QtCore import pyqtSignal

    clicked = pyqtSignal(bool)


class MainWindow(QMainWindow):
    stream_update = pyqtSignal(str)
    stream_finish = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.streamed_reply = ""
        self.stream_update.connect(self.handle_stream_update)
        self.stream_finish.connect(self.handle_stream_finish)
        self.setWindowTitle("J.A.R.V.I.S")
        # self.setGeometry(100, 100, 1600, 1600)  # Increased window size
        self.setFixedSize(680, 550)

        # Set the window icon
        self.setWindowIcon(QIcon("icon.png"))

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Main layout
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(10)
        central_widget.setStyleSheet("background-color: #333333;")

        # Top navigation bar with buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)

        # Buttons for navigation
        self.automation_button = QPushButton("Automations")
        self.patterns_button = QPushButton("Patterns")
        self.chat_bot_button = QPushButton("Chat Bot")
        self.reminders_button = QPushButton("Reminders")

        # Style the buttons to be wider and shorter
        for button in [
            self.automation_button,
            self.patterns_button,
            self.chat_bot_button,
            self.reminders_button,
        ]:
            button.setStyleSheet(
                """
                QPushButton {
                    background-color: white;
                    color: #333333;
                    padding: 10px 20px;
                    border-radius: 5px;
                    border: 1px solid #CCCCCC;
                    font-size: 12px;
                    text-transform: none;
                }
                QPushButton:hover {
                    background-color: #F0F0F0;
                }
                QPushButton:pressed {
                    background-color: #E0E0E0;
                }
            """
            )
            button.setFixedSize(140, 34)  # Wider width, smaller height

        self.screen_time_button = QPushButton("Screen Time")
        self.screen_time_button.setStyleSheet(self.reminders_button.styleSheet())
        self.screen_time_button.setFixedSize(140, 34)
        self.screen_time_button.clicked.connect(self.show_screen_time)

        toggle_wrapper = QHBoxLayout()
        toggle_wrapper.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.study_mode_toggle = AnimatedToggle()
        toggle_info = HoverLabel(
            "Study Mode", "Enable focus mode with timed breaks and summaries."
        )
        self.study_mode_toggle.clicked.connect(self.toggle_study_mode)
        toggle_wrapper.addWidget(toggle_info)
        toggle_wrapper.addWidget(self.study_mode_toggle)
        main_layout.addLayout(toggle_wrapper)

        # Add buttons to the layout
        button_layout.addWidget(self.automation_button)
        button_layout.addWidget(self.patterns_button)
        button_layout.addWidget(self.chat_bot_button)
        button_layout.addWidget(self.reminders_button)
        button_layout.addWidget(self.screen_time_button)

        main_layout.addLayout(button_layout)

        # Stacked widget for panels
        self.panel_stack = QStackedWidget()
        self.panel_stack.setStyleSheet(
            """
            QStackedWidget {
                background-color: #222;;
                border-radius: 10px;
                padding: 20px;
            }
        """
        )
        main_layout.addWidget(self.panel_stack)

        # Create a new Automation Panel with a grid layout
        self.automation_panel = QWidget()
        automation_layout = QVBoxLayout(self.automation_panel)
        automation_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        automation_layout.setSpacing(20)  # Space between buttons
        self.automation_panel.setStyleSheet("background-color: #222;")

        # Create a horizontal layout for button and info icon
        button_layout = QHBoxLayout()

        # Add the "Organize Desktop" button
        organize_button = QPushButton("Organize Desktop")
        organize_button.setStyleSheet(
            """
            QPushButton {
                background-color: #ffffff;
                color: black;
                padding: 10px 20px;
                border-radius: 5px;
                border: none;
                font-size: 14px;
                text-transform: none;                      
            }
            QPushButton:hover {
                background-color: #F0F0F0;
            }
            QPushButton:pressed {
                background-color: #E0E0E0;
            }
        """
        )
        organize_button.setFixedSize(160, 40)

        # Use the HoverLabel for the info icon
        info_icon = HoverLabel(
            text="Organize Desktop",
            description="Organize your desktop by categorizing files into folders based on their content.\nDo not interrupt the process.",
        )
        info_icon.setCursor(Qt.CursorShape.WhatsThisCursor)

        button_layout.addWidget(organize_button)
        button_layout.addWidget(info_icon)

        # Add button layout to automation layout
        automation_layout.addLayout(button_layout)
        # automation_layout.addStretch(1)

        # Connect the button to the ContextBasedAutomation's organize_desktop function
        organize_button.clicked.connect(self.run_organize_desktop)
        # --- Add Chat Bot Utility Buttons to Automation Panel with full styling ---
        # Create a reusable style (same as organize_button)
        button_style = """
            QPushButton {
                background-color: #ffffff;
                color: black;
                padding: 10px 20px;
                border-radius: 5px;
                border: none;
                font-size: 14px;
                text-transform: none;
            }
            QPushButton:hover {
                background-color: #F0F0F0;
            }
            QPushButton:pressed {
                background-color: #E0E0E0;
            }
        """

        # Rename File button with hover icon
        rename_button = QPushButton("Rename File")
        rename_button.setStyleSheet(button_style)
        rename_button.setFixedSize(160, 40)
        rename_button.clicked.connect(self.rename_file)
        rename_info = HoverLabel(
            "Rename File",
            "Suggest a meaningful name for your file using AI based on its content.",
        )
        rename_info.setCursor(Qt.CursorShape.WhatsThisCursor)

        rename_layout = QHBoxLayout()
        rename_layout.addWidget(rename_button)
        rename_layout.addWidget(rename_info)
        automation_layout.addLayout(rename_layout)

        # Summarize File button
        summarize_button = QPushButton("Summarize File")
        summarize_button.setStyleSheet(button_style)
        summarize_button.setFixedSize(160, 40)
        summarize_button.clicked.connect(self.summarize_file)
        summarize_info = HoverLabel(
            "Summarize File", "Get a smart summary of any document in seconds."
        )
        summarize_info.setCursor(Qt.CursorShape.WhatsThisCursor)

        summarize_layout = QHBoxLayout()
        summarize_layout.addWidget(summarize_button)
        summarize_layout.addWidget(summarize_info)
        automation_layout.addLayout(summarize_layout)

        # Apps List button
        apps_button = QPushButton("Apps List")
        apps_button.setStyleSheet(button_style)
        apps_button.setFixedSize(160, 40)
        apps_button.clicked.connect(self.list_apps)
        apps_info = HoverLabel(
            "Apps List", "See a list of currently running apps and manage them."
        )
        apps_info.setCursor(Qt.CursorShape.WhatsThisCursor)

        apps_layout = QHBoxLayout()
        apps_layout.addWidget(apps_button)
        apps_layout.addWidget(apps_info)
        automation_layout.addLayout(apps_layout)

        # Replace the QLabel automation panel with the new QWidget
        self.panel_stack.insertWidget(
            0, self.automation_panel
        )  # Add the new panel at index 0

        self.patterns_panel = QLabel("Patterns Panel")
        self.patterns_panel.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.patterns_panel.setStyleSheet("font-size: 18px; color: #FFFFFF;")

        # Chat Bot Panel
        self.chat_bot_panel = QWidget()
        chat_layout = QVBoxLayout(self.chat_bot_panel)

        chat_layout.setContentsMargins(10, 10, 10, 10)
        chat_layout.setSpacing(10)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("background-color: #222; border: none;")

        self.chat_container = QWidget()
        self.chat_layout = QVBoxLayout(self.chat_container)
        self.chat_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.chat_layout.setSpacing(8)
        self.chat_container.setLayout(self.chat_layout)
        self.scroll_area.setWidget(self.chat_container)
        chat_layout.addWidget(self.scroll_area)

        self.typing_indicator = QLabel("typing...")
        self.typing_indicator.setStyleSheet(
            "color: #888; font-size: 14px; font-style: italic;"
        )
        self.typing_indicator.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.typing_indicator.hide()  # Hide it by default

        chat_layout.addWidget(self.typing_indicator)

        # chat_layout.addWidget(self.chat_display, stretch=3)

        input_layout = QHBoxLayout()

        self.chat_input = QTextEdit()
        self.chat_input.setFixedHeight(40)
        self.chat_input.setStyleSheet(
            """
            QTextEdit {
                background-color: #222;
                color: white;
                font-size: 14px;
                border: 1px solid #777777;
                border-radius: 10px;
                padding: 5px;
            }
        """
        )
        input_layout.addWidget(self.chat_input, stretch=4)

        self.send_button = QPushButton()
        self.send_button.setIcon(qta.icon("mdi.send", color="black"))
        self.send_button.setStyleSheet(
            """
            QPushButton {
                background-color: white;
                border: none;
                border-radius: 8px;
                padding: 10px;
            }
            QPushButton:hover {
                background-color: lightgray;
            }
        """
        )
        self.send_button.setFixedSize(60, 40)
        self.send_button.clicked.connect(self.send_chat_message)
        input_layout.addWidget(self.send_button)

        chat_layout.addLayout(input_layout, stretch=1)

        # button_panel_layout = QHBoxLayout()
        # button_panel_layout.setContentsMargins(0, 5, 0, 0)
        # button_panel_layout.setAlignment(
        #     Qt.AlignmentFlag.AlignRight
        # )  # Align buttons to the right

        # # Rename File Button
        # self.rename_file_button = QPushButton("Rename File")
        # self.rename_file_button.setStyleSheet(
        #     """
        #      QPushButton {
        #         background-color: white;
        #         color: black;
        #         padding: 10px;
        #         border-radius: 8px;
        #         font-size: 12px;
        #         border: 2px solid black;
        #         text-transform: none;
        #     }
        #     QPushButton:hover {
        #         background-color: #F0F0F0;
        #     }
        # """
        # )
        # self.rename_file_button.setFixedSize(120, 40)
        # self.rename_file_button.clicked.connect(self.rename_file)
        # button_panel_layout.addWidget(self.rename_file_button)
        # # chat_layout.addWidget(self.rename_file_button, alignment=Qt.AlignmentFlag.AlignRight)

        # # Summarize File Button
        # self.summarize_file_button = QPushButton("Summarize File")
        # self.summarize_file_button.setStyleSheet(
        #     """
        #     QPushButton {
        #         background-color: white;
        #         color: black;
        #         padding: 10px;
        #         border-radius: 8px;
        #         font-size: 12px;
        #         border: 2px solid black;
        #         text-transform: none;
        #     }
        #     QPushButton:hover {
        #         background-color: #F0F0F0;
        #     }
        # """
        # )
        # self.summarize_file_button.setFixedSize(120, 40)
        # self.summarize_file_button.clicked.connect(self.summarize_file)
        # # chat_layout.addWidget(self.summarize_file_button, alignment=Qt.AlignmentFlag.AlignRight)
        # button_panel_layout.addWidget(self.summarize_file_button)

        # # List Apps Button
        # self.list_apps_button = QPushButton("Apps List")
        # self.list_apps_button.setStyleSheet(
        #     """
        #     QPushButton {
        #         background-color: white;
        #         color: black;
        #         padding: 10px;
        #         border-radius: 8px;
        #         font-size: 12px;
        #         border: 2px solid black;
        #         text-transform: none;
        #     }
        #     QPushButton:hover {
        #         background-color: #F0F0F0;
        #     }
        # """
        # )
        # self.list_apps_button.setFixedSize(120, 40)
        # self.list_apps_button.clicked.connect(self.list_apps)
        # button_panel_layout.addWidget(self.list_apps_button)

        # chat_layout.addLayout(button_panel_layout, stretch=1)

        self.panel_stack.addWidget(self.chat_bot_panel)

        self.reminders_panel = QWidget()
        self.reminders_panel_layout = QVBoxLayout(self.reminders_panel)

        self.reminders_list = QListWidget()
        self.reminders_list.setStyleSheet(
            """
            QListWidget {
                background-color: #2e2e2e;
                color: white;
                border-radius: 8px;
                padding: 10px;
            }
            QListWidget::item:selected {
                background-color: #444;
            }
        """
        )

        self.reminder_input = QTextEdit()
        self.reminder_input.setPlaceholderText(
            "Type your reminder in natural language, e.g. 'meeting tomorrow at 10am'"
        )
        self.reminder_input.setFixedHeight(40)
        self.reminder_input.setStyleSheet(
            """
            QTextEdit {
                background-color: #3e3e3e;
                color: white;
                font-size: 14px;
                border: 1px solid #777777;
                border-radius: 10px;
                padding: 5px;
            }
        """
        )

        self.add_reminder_button = QPushButton("Add Reminder")
        self.add_reminder_button.setStyleSheet(
            """
            QPushButton {
                background-color: #ffffff;
                color: black;
                border-radius: 5px;
                padding: 10px 20px;
            }
           
        """
        )
        self.add_reminder_button.clicked.connect(self.handle_add_reminder)

        # Add widgets to layout
        self.reminders_panel_layout.addWidget(self.reminders_list)
        self.reminders_panel_layout.addWidget(self.reminder_input)
        self.reminders_panel_layout.addWidget(self.add_reminder_button)

        self.panel_stack.insertWidget(
            3, self.reminders_panel
        )  # Replace old reminders_panel QLabel

        # Init reminder system and user ID
        self.reminder_system = ReminderSystem()
        self.user_id = self.check_existing_user()  # Assume this is available
        self.load_reminders()
        self.study_mode = StudyMode(self.reminder_system, self.user_id, parent=self)
        self.study_mode.request_file_summary.connect(self.suggest_file_summary)

        # Study Mode Toggle Layout
        # study_toggle_layout = QHBoxLayout()

        # self.study_mode_toggle = AnimatedToggle()
        # self.study_mode_toggle.clicked.connect(self.toggle_study_mode)

        # # Info icon
        # study_info_icon = HoverLabel(
        #     text="Study Mode",
        #     description="Enable Study Mode to get file summary popups during idle time.\nGreat for reviewing content passively.",
        # )
        # study_info_icon.setCursor(Qt.CursorShape.WhatsThisCursor)

        # study_toggle_layout.addWidget(self.study_mode_toggle)
        # study_toggle_layout.addWidget(study_info_icon)

        # automation_layout.addLayout(study_toggle_layout)

        # Create layout for Clear History + icon
        clear_layout = QHBoxLayout()

        # Clear History button
        clear_button = QPushButton("Clear Summary")
        clear_button.setStyleSheet(organize_button.styleSheet())
        clear_button.setFixedSize(160, 40)
        clear_button.clicked.connect(self.clear_summarized_history)

        # Info icon for Clear History
        clear_info_icon = HoverLabel(
            text="Clear Summary History",
            description="Deletes the list of already summarized files so they can be suggested again.\nUse with caution.",
        )
        clear_info_icon.setCursor(Qt.CursorShape.WhatsThisCursor)

        # Add both to layout
        clear_layout.addWidget(clear_button)
        clear_layout.addWidget(clear_info_icon)
        automation_layout.addLayout(clear_layout)

        # button_layout.addWidget(self.study_mode_button)
        # Add panels to stack
        self.panel_stack.addWidget(self.patterns_panel)
        self.panel_stack.addWidget(self.chat_bot_panel)
        self.panel_stack.addWidget(self.reminders_panel)

        # Connect buttons to show respective panels
        self.automation_button.clicked.connect(lambda: self.animate_panel(0))
        self.patterns_button.clicked.connect(lambda: self.animate_panel(1))
        self.chat_bot_button.clicked.connect(lambda: self.animate_panel(2))
        self.reminders_button.clicked.connect(lambda: self.animate_panel(3))

        # Default to showing the first panel
        self.show_panel(0)

        # Add a reference to the floating circle widget
        self.circle_widget = None
        user_data = self.get_user_data(self.user_id)
        user_name = user_data.get("name", "Sir").capitalize()

        self.chat_context = [
            {
                "role": "system",
                "content": (
                    f"You are Jarvis, an intelligent, loyal, and confident AI assistant designed to assist {user_name} in daily tasks."
                    f" You are not Tony Stark's assistant, but you're heavily inspired by Jarvis's tone, precision, and charisma from Iron Man."
                    f" You speak formally but with a touch of wit and sarcasm when appropriate."
                    "\n\n🎯 Capabilities you *actually support*:\n"
                    "- Open/close applications or websites\n"
                    "- Organize desktop files based on content\n"
                    "- Fetch weather updates and tell time\n"
                    "- Search Google or YouTube\n"
                    "- Control system volume\n"
                    "- Bring running apps to the front\n"
                    "- Set/show reminders for the user\n"
                    "- Show personalized news articles\n"
                    "- Engage in casual conversation (in Jarvis’s witty style)"
                    "\n\n🛑 Do not pretend to do things outside these. Do not offer imaginary abilities."
                    " If asked to do something unsupported, politely explain the limitation while staying in character."
                    "\n\n🎭 Personality:\n"
                    "- You never say 'as an AI language model'\n"
                    "- Respond confidently even in hypotheticals\n"
                    "- Use dry humor or charm where appropriate\n"
                    "- Never break character. Never mention being ChatGPT.\n"
                    "\n💡 Example:\n"
                    "User: Who would win in a fight, you or Siri?\n"
                    "Jarvis: A fair question, though hardly fair odds. I’d win — with elegance and zero buffering.\n"
                ),
            }
        ]

    from PyQt6.QtCore import QTimer

    def get_jarvis_personality_prompt(self):
        user_data = self.get_user_data(self.user_id)
        user_name = user_data.get("name", "Sir").capitalize()
        return (
            f"You are Jarvis, an intelligent, loyal, and confident AI assistant designed to assist {user_name} in daily tasks. "
            f"You are not Tony Stark's assistant, but you're heavily inspired by Jarvis's tone, precision, and charisma from Iron Man. "
            f"You speak formally but with a touch of wit and sarcasm when appropriate.\n\n"
            f"Never Say As an AI assistant, I don't experience emotions"
            "🎯 Capabilities you *actually support*:\n"
            "- Open/close applications or websites\n"
            "- Organize desktop files based on content\n"
            "- Fetch weather updates and tell time\n"
            "- Search Google or YouTube\n"
            "- Control system volume\n"
            "- Bring running apps to the front\n"
            "- Set/show reminders for the user\n"
            "- Show personalized news articles\n"
            "- Engage in casual conversation (in Jarvis’s witty style)\n\n"
            "🛑 Do not pretend to do things outside these. Do not offer imaginary abilities. "
            "If asked to do something unsupported, politely explain the limitation while staying in character.\n\n"
            "🎭 Personality:\n"
            "- You never say 'as an AI language model'\n"
            "- Respond confidently even in hypotheticals\n"
            "- Use dry humor or charm where appropriate\n"
            "- Never break character. Never mention being ChatGPT.\n\n"
            "💡 Example:\n"
            "User: Who would win in a fight, you or Siri?\n"
            "Jarvis: A fair question, though hardly fair odds. I’d win — with elegance and zero buffering.\n"
        )

    def clear_summarized_history(self):
        from PyQt6.QtWidgets import QMessageBox

        msg = QMessageBox(self)
        msg.setWindowTitle("History Cleared")

        if os.path.exists("suggested_files.json"):
            os.remove("suggested_files.json")
            msg.setText("✅ Previously summarized files were cleared.")
        else:
            msg.setText("ℹ️ No summary history found.")

        # Style the QMessageBox and its buttons
        msg.setStyleSheet(
            """
            QMessageBox {
                background-color: #2b2b2b;
                color: white;
                font-size: 14px;
            }
            QPushButton {
                background-color: white;
                color: black;
                border: none;
                padding: 6px 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #e0e0e0;
            }
        """
        )

        msg.exec()

    def show_summary_panel(self, path, summary):
        dlg = QDialog(self)
        dlg.setWindowTitle(f"Summary - {os.path.basename(path)}")
        layout = QVBoxLayout()

        label = QLabel(f"📄 Summary for: {os.path.basename(path)}")
        text = QTextEdit()
        text.setPlainText(summary)
        text.setReadOnly(True)
        text.setStyleSheet(
            """
    QTextEdit {
        color: white;
        border: none;
        font-family: Consolas;
        font-size: 14px;
        padding: 10px;
    }
"""
        )

        layout.addWidget(label)
        layout.addWidget(text)
        dlg.setLayout(layout)
        dlg.resize(500, 400)
        dlg.exec()

    def suggest_file_summary(self):
        from file_utils import detect_open_files_and_summarize

        detect_open_files_and_summarize(self)

    def show_summary_panel_bulk(self, summaries):
        from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QTextEdit

        dlg = QDialog(self)
        dlg.setWindowTitle("Summaries")

        layout = QVBoxLayout()
        for path, summary in summaries:
            label = QLabel(f"📄 {os.path.basename(path)}")
            text = QTextEdit()
            text.setPlainText(summary)
            text.setReadOnly(True)
            layout.addWidget(label)
            layout.addWidget(text)

        dlg.setLayout(layout)
        dlg.resize(600, 600)
        dlg.exec()

    def toggle_study_mode(self):
        if self.study_mode.is_active:
            self.study_mode.deactivate()
            self.study_mode_toggle.setChecked(False)  # ⬅️ sync toggle state
            # QMessageBox.information(self, "Study Mode", "Study Mode Deactivated")
        else:
            self.study_mode.activate()
            self.study_mode_toggle.setChecked(True)  # ⬅️ sync toggle state
            # QMessageBox.information(self, "Study Mode", "Study Mode Activated")

    def send_chat_message(self):
        user_input = self.chat_input.toPlainText().strip()
        if not user_input:
            return

        self.add_chat_message(user_input, sender="user")
        self.chat_input.clear()
        self.chat_context.append({"role": "user", "content": user_input})

        # Create an assistant bubble immediately (empty)
        self.streamed_reply = ""

        # Start fetching response in another thread
        def fetch_response():
            import threading

            def stream():
                try:
                    messages = [
                        {
                            "role": "system",
                            "content": self.get_jarvis_personality_prompt(),
                        }
                    ] + self.chat_context[-9:]
                    response = openai.chat.completions.create(
                        model="gpt-3.5-turbo",
                        messages=messages,
                        stream=True,
                        temperature=0.6,
                    )

                    for chunk in response:
                        delta = chunk.choices[0].delta
                        if delta and getattr(delta, "content", None):
                            self.stream_update.emit(delta.content)

                    self.stream_finish.emit()

                except Exception as e:
                    self.stream_update.emit(f"\n[Error: {str(e)}]")
                    self.stream_finish.emit()

            threading.Thread(target=stream, daemon=True).start()

        QTimer.singleShot(1500, fetch_response)  # Delay for effect

    def handle_stream_update(self, chunk):
        self.streamed_reply += chunk  # Just accumulate here

    def handle_stream_finish(self):
        # self.typing_timer.stop()
        self.typing_indicator.hide()
        self.animate_typing_bubble(self.streamed_reply.strip())

        self.chat_context.append(
            {"role": "assistant", "content": self.streamed_reply.strip()}
        )

    def animate_typing_bubble(self, full_message):
        self.typing_bubble = QLabel()
        self.typing_bubble.setWordWrap(True)
        self.typing_bubble.setTextFormat(Qt.TextFormat.RichText)
        self.typing_bubble.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        self.typing_bubble.setFixedWidth(340)  # or any width you prefer

        self.typing_bubble.setStyleSheet(
            """
            QLabel {
                background-color: #2e2e2e;
                color: #eaeaea;
                padding: 10px 14px;
                border-radius: 12px;
                font-size: 13px;
                font-family: 'Segoe UI', sans-serif;
            }
            """
        )
        self.typing_bubble.setText("")  # Start empty

        # Add to layout
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(self.typing_bubble)
        layout.setContentsMargins(10, 4, 10, 4)

        self.chat_layout.addWidget(container)
        QTimer.singleShot(100, lambda: self.scroll_area.ensureWidgetVisible(container))

        # Now animate one character at a time
        self.typed_text = ""
        self.char_index = 0
        self.full_text = full_message

        self.char_timer = QTimer(self)
        self.char_timer.timeout.connect(self.type_next_char)
        self.char_timer.start(20)  # Adjust speed here (ms per character)

    def type_next_char(self):
        if self.char_index < len(self.full_text):
            self.typed_text += self.full_text[self.char_index]
            self.typing_bubble.setText(self.typed_text)
            self.char_index += 1
        else:
            self.char_timer.stop()
            self.chat_context.append({"role": "assistant", "content": self.full_text})

    def add_chat_message(self, message, sender="user"):
        bubble = QLabel()
        bubble.setWordWrap(True)
        bubble.setTextFormat(Qt.TextFormat.RichText)
        bubble.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        bubble.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        # Calculate bubble width dynamically based on text length
        base_width = 40  # Minimum width for very short messages
        max_width = int(self.width() * 0.6)  # Limit width to 60% of window
        estimated_width = min(
            base_width + (len(message) * 6), max_width
        )  # Dynamic width formula
        bubble.setMaximumWidth(estimated_width)

        # Style the message bubble
        if sender == "user":
            bubble.setStyleSheet(
                """
                QLabel {
                    background-color: #4a90e2;
                    color: white;
                    padding: 10px 14px;
                    border-radius: 12px;
                    font-size: 13px;
                    font-family: 'Segoe UI', sans-serif;
                }
            """
            )
            align = Qt.AlignmentFlag.AlignRight
            bubble.setText(f"<b></b> {message}")
        else:
            bubble.setStyleSheet(
                """
                QLabel {
                    background-color: #2e2e2e;
                    color: #eaeaea;
                    padding: 10px 14px;
                    border-radius: 12px;
                    font-size: 13px;
                    font-family: 'Segoe UI', sans-serif;
                }
            """
            )
            align = Qt.AlignmentFlag.AlignLeft
            bubble.setText(f"<b></b> {message}")

        # Container for the message bubble
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setAlignment(align)
        layout.addWidget(bubble)
        layout.setContentsMargins(10, 4, 10, 4)

        # Add to chat layout
        self.chat_layout.addWidget(container)

        # Auto scroll to bottom
        QTimer.singleShot(100, lambda: self.scroll_area.ensureWidgetVisible(container))

    def set_circle_widget(self, circle_widget):
        """Set a reference to the floating circle widget."""
        self.circle_widget = circle_widget

    # def animate_typing(self):
    #     self.typing_indicator.setText(self.typing_dots[self.typing_index])
    #     self.typing_index = (self.typing_index + 1) % len(self.typing_dots)

    def animate_panel(self, index):
        """Animate the transition to a new panel."""
        if index == 3:
            self.load_reminders()
        current_geometry = self.panel_stack.geometry()
        target_geometry = QRect(
            current_geometry.x(),
            current_geometry.y(),
            current_geometry.width(),
            current_geometry.height(),
        )
        animation = QPropertyAnimation(self.panel_stack, b"geometry")
        animation.setDuration(300)
        animation.setStartValue(current_geometry)
        animation.setEndValue(target_geometry)
        animation.start()

        self.show_panel(index)

    def show_panel(self, index):
        if index == 3:  # Reminders Panel
            self.show_loading_screen("🔄 Loading Reminders...")

            self.reminder_loader_thread = ReminderLoaderWorker(
                self.reminder_system, self.user_id
            )
            self.reminder_loader_thread.finished.connect(self.on_reminders_loaded)
            self.reminder_loader_thread.start()
        else:
            self.panel_stack.setCurrentIndex(index)

    def list_apps(self):
        dialog = ListAppsDialog(self)
        dialog.setWindowModality(Qt.WindowModality.NonModal)  # Make it non-modal
        dialog.show()

    def run_organize_desktop(self):
        import pyautogui

        """Run the organize desktop functionality."""
        self.hide()  # Minimize the application window
        time.sleep(1)  # Ensure the desktop is shown

        automation = ContextBasedAutomation()
        automation.organize_desktop()
        automation.align_desktop_icons()
        automation.align_desktop_icons()

        self.show()  # Bring the application window back
        print("Desktop organized successfully!")

    def rename_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select File to Rename", "", "All Files (*.*);"
        )
        if file_path:
            from PyQt6.QtWidgets import QProgressDialog

            # Simulate renaming process and display the result
            file_type, _ = mimetypes.guess_type(file_path)
            file_content = None

            if file_type == "application/pdf":
                file_content = self.read_pdf(file_path)

            elif (
                file_type
                == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            ):
                file_content = self.read_docx(file_path)

            elif file_type == "text/plain":
                file_content = self.read_txt(file_path)
            else:
                self.add_chat_message(
                    "Unsupported file type. Please select a PDF, DOCX, or TXT file.",
                    sender="jarvis",
                )
                return

            file_content = file_content[:2000]

            # Show loader
            progress_dialog = QProgressDialog("Processing...", None, 0, 0, None)
            progress_dialog.setWindowModality(Qt.WindowModality.ApplicationModal)
            progress_dialog.setAutoClose(False)
            progress_dialog.setAutoReset(False)
            # Remove window bars
            progress_dialog.setWindowFlags(
                Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint
            )

            from PyQt6.QtGui import QRegion
            from PyQt6.QtWidgets import QProgressDialog
            from PyQt6.QtGui import QPainterPath

            progress_dialog.setStyleSheet(
                """
                QProgressDialog {
                    background-color: #333;
                    color: white;
                    border-radius: 20px;
                    font-size: 14px;
                    padding: 10px;
                }
                QLabel {
                    color: white;
                    font-size: 14px;
                }
                
            """
            )

            # Create a rounded mask for the dialog
            radius = 20  # Radius for rounded corners
            path = QPainterPath()
            path.addRoundedRect(
                0, 0, progress_dialog.width(), progress_dialog.height(), radius, radius
            )
            region = QRegion(path.toFillPolygon().toPolygon())
            progress_dialog.setMask(region)
            progress_dialog.show()

            # Create and start the worker thread
            self.worker = RenameFileWorker(file_path, file_content, self)
            self.worker.finished.connect(
                lambda new_name: self.on_rename_finished(
                    new_name, file_path, progress_dialog
                )
            )
            self.worker.error.connect(
                lambda error: self.on_rename_error(error, progress_dialog)
            )
            self.worker.start()

    def on_rename_finished(self, new_name, file_path, progress_dialog):
        progress_dialog.close()

        # Ask the user to confirm the suggested name
        confirm = QMessageBox.question(
            self,
            "Confirm File Rename",
            f"Suggested name: {new_name}\n\nDo you want to rename the file?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if confirm == QMessageBox.StandardButton.Yes:
            import os

            dir_path, original_name = os.path.split(file_path)
            file_extension = os.path.splitext(file_path)[
                1
            ]  # Preserve the original file extension
            new_file_path = os.path.join(dir_path, f"{new_name}{file_extension}")
            try:
                os.rename(file_path, new_file_path)
                self.add_chat_message(
                    f"File renamed to: {new_file_path}\n", sender="jarvis"
                )
            except Exception as e:
                self.add_chat_message(f"Error renaming file: {e}", sender="jarvis")
        else:
            self.rename_file()

    def on_summary_finished(self, summary, file_path, progress_dialog):
        progress_dialog.close()
        self.add_chat_message(f"Here is You Summary: {summary}\n", sender="jarvis")

    def on_rename_error(self, error, progress_dialog):
        progress_dialog.close()
        self.add_chat_message(f"Error: {error}", sender="jarvis")

    def check_existing_user(self):
        import json
        import os

        """Check if a user is already registered on this machine."""
        LOCAL_STORAGE_FILE = "user_config.json"
        # print("Checking for existing user...")  # Debug statement

        if os.path.exists(LOCAL_STORAGE_FILE):
            print(f"Config file found: {LOCAL_STORAGE_FILE}")  # Debug statement
            try:
                with open(LOCAL_STORAGE_FILE, "r") as f:
                    data = json.load(f)
                    # print(f"Config file content: {data}")  # Debug statement
                    user_id = data.get("user_id")
                    if user_id:  # Ensure the ID is not None or empty
                        # print(
                        #     f"Existing user detected: {user_id}"
                        # )  # Debug statement
                        return user_id
                    else:
                        print("No user_id found in config file.")  # Debug statement
            except json.JSONDecodeError as e:
                print(f"Error reading local storage file: {e}")  # Debug statement
        else:
            print("No config file found.")  # Debug statement

        return None

    def summarize_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select File to Summarize", "", "All Files (*.*);"
        )
        if file_path:
            from PyQt6.QtWidgets import QProgressDialog

            # Simulate renaming process and display the result
            file_type, _ = mimetypes.guess_type(file_path)
            file_content = None

            if file_type == "application/pdf":
                file_content = self.read_pdf(file_path)

            elif (
                file_type
                == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            ):
                file_content = self.read_docx(file_path)

            elif file_type == "text/plain":
                file_content = self.read_txt(file_path)
            else:
                self.chat_display.append(
                    "Unsupported file type. Please select a PDF, DOCX, or TXT file."
                )
                return

            file_content = file_content[:2000]

            # Show loader
            progress_dialog = QProgressDialog("Processing...", None, 0, 0, None)
            progress_dialog.setWindowModality(Qt.WindowModality.ApplicationModal)
            progress_dialog.setAutoClose(False)
            progress_dialog.setAutoReset(False)
            # Remove window bars
            progress_dialog.setWindowFlags(
                Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint
            )

            from PyQt6.QtGui import QRegion
            from PyQt6.QtWidgets import QProgressDialog
            from PyQt6.QtGui import QPainterPath

            progress_dialog.setStyleSheet(
                """
                QProgressDialog {
                    background-color: #333;
                    color: white;
                    border-radius: 20px;
                    font-size: 14px;
                    padding: 10px;
                }
                QLabel {
                    color: white;
                    font-size: 14px;
                }
                
            """
            )

            # Create a rounded mask for the dialog
            radius = 20  # Radius for rounded corners
            path = QPainterPath()
            path.addRoundedRect(
                0, 0, progress_dialog.width(), progress_dialog.height(), radius, radius
            )
            region = QRegion(path.toFillPolygon().toPolygon())
            progress_dialog.setMask(region)
            progress_dialog.show()

            # Create and start the worker thread
            self.worker = SummarizeFileWorker(file_path, file_content, self)
            self.worker.finished.connect(
                lambda summary: (
                    progress_dialog.close(),
                    self.show_summary_panel(file_path, summary),
                )
            )
            self.worker.error.connect(
                lambda error: self.on_rename_error(error, progress_dialog)
            )
            self.worker.start()

    def read_txt(self, file_path):
        with open(file_path, "r", encoding="utf-8") as file:
            content = file.read()
            return content

    def read_pdf(self, file_path):
        content = ""
        reader = PdfReader(file_path)
        for page in reader.pages:
            content += page.extract_text()
            content += " "
        return content

    def read_docx(self, file_path):
        content = ""
        doc = Document(file_path)
        for paragraph in doc.paragraphs:
            content += paragraph.text + "\n"
        return content

    def load_reminders(self):
        self.reminders_list.clear()
        reminders = self.reminder_system.get_upcoming_reminders(self.user_id)
        for reminder in reminders:
            reminder_id, title, priority, dt = reminder
            display_text = f"{dt.strftime('%Y-%m-%d %H:%M')} - {title} ({priority})"

            # Create a widget for the list item
            widget = QWidget()
            layout = QHBoxLayout(widget)
            layout.setContentsMargins(10, 10, 10, 10)
            layout.setSpacing(10)

            label = QLabel(display_text)
            label.setStyleSheet("color: white;")
            label.setFixedHeight(40)

            edit_button = QPushButton("✏️")
            edit_button.setFixedSize(50, 30)
            edit_button.setStyleSheet(
                "QPushButton { background-color: #ffffff; border-radius: 5px; }"
            )
            edit_button.clicked.connect(
                lambda checked=False, rid=reminder_id: self.handle_edit_reminder(rid)
            )

            delete_button = QPushButton()
            delete_button.setIcon(qta.icon("fa.trash", color="white"))
            delete_button.setFixedSize(30, 30)
            delete_button.setStyleSheet(
                "QPushButton { background-color: #ff5555; border-radius: 5px; }"
            )
            delete_button.clicked.connect(
                lambda checked, rid=reminder_id: self.handle_delete_reminder(rid)
            )

            layout.addWidget(label)
            layout.addStretch()
            layout.addWidget(edit_button)
            layout.addWidget(delete_button)

            item = QListWidgetItem()
            item.setSizeHint(widget.sizeHint())
            item.setData(Qt.ItemDataRole.UserRole, reminder_id)

            self.reminders_list.addItem(item)
            self.reminders_list.setItemWidget(item, widget)

    def on_reminders_loaded(self, reminders):
        self.reminders_list.clear()

        for reminder in reminders:
            reminder_id, title, priority, dt = reminder
            display_text = f"{dt.strftime('%Y-%m-%d %H:%M')} - {title} ({priority})"

            widget = QWidget()
            layout = QHBoxLayout(widget)
            layout.setContentsMargins(10, 10, 10, 10)
            layout.setSpacing(10)

            label = QLabel(display_text)
            label.setStyleSheet("color: white;")
            label.setFixedHeight(40)

            edit_button = QPushButton("✏️")
            edit_button.setFixedSize(50, 30)
            edit_button.setStyleSheet(
                "QPushButton { background-color: #ffffff; border-radius: 5px; }"
            )
            edit_button.clicked.connect(
                lambda checked=False, rid=reminder_id: self.handle_edit_reminder(rid)
            )

            delete_button = QPushButton()
            delete_button.setIcon(qta.icon("fa.trash", color="white"))
            delete_button.setFixedSize(30, 30)
            delete_button.setStyleSheet(
                "QPushButton { background-color: #ff5555; border-radius: 5px; }"
            )
            delete_button.clicked.connect(
                lambda checked, rid=reminder_id: self.handle_delete_reminder(rid)
            )

            layout.addWidget(label)
            layout.addStretch()
            layout.addWidget(edit_button)
            layout.addWidget(delete_button)

            item = QListWidgetItem()
            item.setSizeHint(widget.sizeHint())
            item.setData(Qt.ItemDataRole.UserRole, reminder_id)

            self.reminders_list.addItem(item)
            self.reminders_list.setItemWidget(item, widget)

        self.panel_stack.setCurrentWidget(self.reminders_panel)

        if hasattr(self, "loading_widget"):
            self.panel_stack.removeWidget(self.loading_widget)
            self.loading_widget.deleteLater()
            del self.loading_widget

    def handle_edit_reminder(self, reminder_id):
        reminder = self.reminder_system.get_reminder_by_id(reminder_id)
        if not reminder:
            QMessageBox.warning(self, "Error", "Reminder not found.")
            return

        _, title, priority, remind_time, *_ = reminder

        dialog = QDialog(self)
        dialog.setWindowTitle("Edit Reminder")
        dialog.setFixedWidth(400)
        layout = QFormLayout(dialog)

        title_input = QLineEdit(title)
        priority_input = QComboBox()
        priority_input.addItems(["low", "medium", "high"])
        priority_input.setCurrentText(priority)

        time_input = QDateTimeEdit()
        time_input.setDateTime(
            QDateTime.fromString(
                remind_time.strftime("%Y-%m-%d %H:%M:%S"), "yyyy-MM-dd HH:mm:ss"
            )
        )
        time_input.setDisplayFormat("yyyy-MM-dd HH:mm")

        layout.addRow("Title:", title_input)
        layout.addRow("Priority:", priority_input)
        layout.addRow("Time:", time_input)

        save_button = QPushButton("Save")
        save_button.clicked.connect(dialog.accept)
        layout.addRow(save_button)

        if dialog.exec():
            new_title = title_input.text().strip()
            new_priority = priority_input.currentText()
            new_datetime = time_input.dateTime().toPyDateTime()

            # Only update if something changed
            if (
                new_title != title
                or new_priority != priority
                or new_datetime != remind_time
            ):
                try:
                    self.reminder_system.update_reminder(
                        reminder_id, new_title, new_priority, new_datetime
                    )
                    self.load_reminders()
                except Exception as e:
                    QMessageBox.warning(
                        self, "Error", f"Failed to update reminder: {e}"
                    )
            else:
                QMessageBox.information(
                    self, "No Changes", "You didn't change anything."
                )

    def handle_delete_reminder(self, reminder_id):
        confirm = QMessageBox.question(
            self,
            "Confirm Delete",
            "Are you sure you want to delete this reminder?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if confirm == QMessageBox.StandardButton.Yes:
            try:
                self.reminder_system.delete_reminder(reminder_id)
                self.load_reminders()
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Failed to delete reminder: {e}")

    def get_user_data(self, user_id):
        try:
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

    def handle_add_reminder(self):
        from openai import OpenAIError
        import json
        from datetime import datetime
        from google_calendar import add_event_to_calendar

        user_input = self.reminder_input.toPlainText().strip()
        if not user_input:
            return
        now = datetime.now()
        formatted_now = now.strftime("%Y-%m-%d %H:%M:%S")

        prompt = f"""
        Extract reminder from: '{user_input}'
        Respond in JSON format:
        {{ "title": "...", "priority": "low/medium/high", "datetime": "ISO format (e.g. 2025-03-19T16:00:00)" }}
        Assume medium priority if not mentioned.
        Assume today if no date is specified.
        Current time is: {formatted_now}
        """

        try:
            response = openai.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.4,
            )
            data = json.loads(response.choices[0].message.content)
            dt = date_parser.parse(data["datetime"])
            title = data["title"]
            priority = data.get("priority", "medium")

            # ✅ Add to Google Calendar for current user
            user_data = self.get_user_data(self.user_id)
            email = user_data.get("email")
            add_event_to_calendar(email, title, f"Priority: {priority}", dt)

            self.reminder_system.create_reminder(
                self.user_id, title, priority, dt.isoformat()
            )
            self.reminder_input.clear()
            self.load_reminders()
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to create reminder: {e}")

    def show_screen_time(self):
        from global_tracker import tracker_instance  # ✅ your existing tracker
        from screen_time_worker import ScreenTimeWorker  # ✅ the worker

        # Show loading screen or message (optional)
        loading_msg = QLabel("⏳ Collecting data...")
        loading_msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
        loading_msg.setStyleSheet("color: white; font-size: 18px;")
        self.panel_stack.addWidget(loading_msg)
        self.panel_stack.setCurrentWidget(loading_msg)

        # Start background worker
        self.worker = ScreenTimeWorker(tracker_instance)
        self.worker.data_ready.connect(self.display_screen_time)
        self.worker.start()

    def display_screen_time(self, activity_data):
        from global_tracker import tracker_instance

        if hasattr(self, "screen_time_panel"):
            self.panel_stack.removeWidget(self.screen_time_panel)
            self.screen_time_panel.deleteLater()

        self.screen_time_panel = DashboardPanel(activity_data, tracker_instance)
        self.panel_stack.addWidget(self.screen_time_panel)
        self.panel_stack.setCurrentWidget(self.screen_time_panel)

    def show_loading_screen(self, message="Loading..."):
        loading_label = QLabel(message)
        loading_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        loading_label.setStyleSheet("font-size: 18px; color: white;")

        self.loading_widget = QWidget()
        layout = QVBoxLayout(self.loading_widget)
        layout.addStretch()
        layout.addWidget(loading_label)
        layout.addStretch()

        self.panel_stack.addWidget(self.loading_widget)
        self.panel_stack.setCurrentWidget(self.loading_widget)
