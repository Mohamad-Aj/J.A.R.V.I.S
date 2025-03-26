from PyQt6.QtWidgets import QWidget, QLabel, QPushButton, QVBoxLayout, QApplication
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QGraphicsDropShadowEffect
from PyQt6.QtGui import QColor
import threading
from playsound import playsound


class ReminderPopup(QWidget):
    def __init__(self, title, reminder_id=None, reminder_system=None):
        super().__init__()
        self.reminder_id = reminder_id
        self.reminder_system = reminder_system

        self.setWindowTitle("")  # No window title
        self.setFixedSize(320, 160)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        # Drop shadow effect
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 180))
        shadow.setOffset(0, 4)
        self.setGraphicsEffect(shadow)

        # Main layout with rounded container
        container = QWidget()
        container.setStyleSheet(
            """
            QWidget {
                background-color: #1e1e1e;
                border-radius: 20px;
            }
        """
        )
        layout = QVBoxLayout(container)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        # Title (not styled as a button)
        label = QLabel(f"{title}")
        label.setWordWrap(True)
        label.setStyleSheet(
            """
            QLabel {
                font-size: 16px;
                font-weight: bold;
                color: #ffffff;
            }
        """
        )
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(label)

        # Snooze Button (blue)
        btn_snooze = QPushButton("Snooze 10 min")
        btn_snooze.setStyleSheet(
            """
            QPushButton {
                background-color: #448aff;
                color: white;
                border-radius: 10px;
                padding: 8px 16px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #2979ff;
            }
        """
        )
        btn_snooze.clicked.connect(self.snooze)
        layout.addWidget(btn_snooze)

        # Dismiss Button (red)
        btn_dismiss = QPushButton("Dismiss")
        btn_dismiss.setStyleSheet(
            """
            QPushButton {
                background-color: #ff5252;
                color: white;
                border-radius: 10px;
                padding: 8px 16px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #ff1744;
            }
        """
        )
        btn_dismiss.clicked.connect(self.dismiss)
        layout.addWidget(btn_dismiss)

        # Final layout
        wrapper = QVBoxLayout(self)
        wrapper.setContentsMargins(0, 0, 0, 0)
        wrapper.addWidget(container)

        # Start sound
        threading.Thread(target=self.play_sound, daemon=True).start()

    def play_sound(self):
        try:
            playsound("alarm.mp3")
        except Exception as e:
            print(f"Sound error: {e}")

    def snooze(self):
        if self.reminder_system and self.reminder_id:
            self.reminder_system.snooze_reminder(self.reminder_id, minutes=10)
        self.close()

    def dismiss(self):
        if self.reminder_system and self.reminder_id:
            self.reminder_system.mark_as_completed(self.reminder_id)
        self.close()

    def move_to_bottom_right(self):
        screen_geometry = QApplication.primaryScreen().geometry()
        x = screen_geometry.width() - self.width() - 20
        y = screen_geometry.height() - self.height() - 40
        self.move(x, y)

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


# popup_launcher.py

from PyQt6.QtWidgets import QApplication
from ReminderSystem import ReminderSystem
import sys


def launch_reminder_popup(reminder_id: str):
    system = ReminderSystem()
    reminder = system.get_reminder_by_id(reminder_id)

    if reminder:
        _, title, _, _, _, _, _ = reminder
        app = QApplication(sys.argv)
        popup = ReminderPopup(title, reminder_id, system)
        popup.show()
        popup.move_to_bottom_right()
        sys.exit(app.exec())
