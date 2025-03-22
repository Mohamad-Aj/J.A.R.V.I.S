import threading
import sys
import math
import qtawesome as qta
import psycopg2
from psycopg2.extras import DictCursor
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QPushButton,
    QLabel,
    QLineEdit,
)
from PyQt6.QtCore import Qt, QTimer, QPoint, QPropertyAnimation, QEasingCurve, QSize
from PyQt6.QtGui import QPainter, QBrush, QColor, QPen, QRadialGradient
from qt_material import apply_stylesheet
from wizard import RegistrationWizard
from PyQt6.QtWidgets import QApplication
from ReminderSystem import ReminderSystem
import os
import json
from main_window import MainWindow
import keyboard  # For global hotkey
from PyQt6.QtCore import pyqtSignal
from audio_assistance import JarvisAssistant
from floating_input import FloatingInputBar


class FloatingCircle(QWidget):

    restore_signal = pyqtSignal()
    hide_signal = pyqtSignal()

    def __init__(self, app_window, parent=None):
        super().__init__(parent)
        self.mic_active = False  # Initialize mic as inactive
        access_key = "51guALrayQ3YkkDW2V7l6r3VJUnRJXnRnBG7fxG1yapci2kz2Tfrqg=="
        self.assistant = JarvisAssistant(
            access_key, keyword="jarvis"
        )  # Instantiate JarvisAssistant

        # Reference to the main app window
        self.app_window = app_window

        self.restore_signal.connect(self._restore_circle)
        self.hide_signal.connect(self._hide_circle)
        # Circle properties
        self.setFixedSize(150, 150)  # Increased size to accommodate buttons
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        # Dragging properties
        self.dragging = False
        self.offset = QPoint()

        # Wave animation properties
        self.wave_timer = QTimer(self)
        self.wave_phase = 0
        self.wave_timer.timeout.connect(self.update_wave_animation)
        self.wave_timer.start(30)  # Adjust speed of the wave animation

        # Buttons and their animations
        self.buttons = []  # List to hold button references
        self.button_animations = []  # Animations for sliding reveal
        self.buttons_visible = False  # Track visibility state
        self.init_buttons_around_circle()
        self.input_bar = FloatingInputBar(parent=self.parent())
        self.input_bar.send_button.clicked.connect(self.handle_send_input)

        # Minimized state
        self.is_minimized = False

        # Setup global hotkey
        self.setup_global_shortcut()

        # Thread lock for synchronized operations
        self.lock = threading.Lock()

        # Input bar for send functionality

    def setup_global_shortcut(self):
        """Set up a global shortcut using the keyboard library."""
        keyboard.add_hotkey("ctrl+shift+j", self.restore_circle)

    def init_input_bar(self):
        from PyQt6.QtWidgets import QLineEdit

        self.input_bar = QLineEdit(self.parent())
        self.input_bar.setPlaceholderText("Type a message...")
        self.input_bar.setStyleSheet(
            """
            QLineEdit {
                background-color: #1e1e1e;
                color: white;
                border: 2px solid #888;
                border-radius: 8px;
                padding: 6px;
                font-size: 13px;
            }
        """
        )
        self.input_bar.setFixedSize(180, 30)

        # Position the input below the circle (centered)
        self.input_bar.move(
            self.width() // 2 - 90, self.height() - 40
        )  # 90 is half width

        self.input_bar.hide()
        self.input_bar.returnPressed.connect(self.process_send_message)

        print("✅ Input bar initialized")

    def init_buttons_around_circle(self):
        """Initialize the buttons in a semi-circular layout along the upper half of the circle."""
        radius = 63  # Radius of the imaginary circle for button placement
        center = QPoint(self.width() // 2, self.height() // 2)  # Center of the circle

        buttons = [
            {
                "icon": "mdi.microphone-off",
                "active_icon": "mdi.microphone",
                "handler": self.handle_mic_click,
            },
            {"icon": "mdi.fullscreen", "handler": self.handle_fullscreen_click},
            {"icon": "mdi.send", "handler": self.handle_send_click},
            {"icon": "mdi.close", "handler": self.handle_close_click},
            {
                "icon": "mdi.power",
                "handler": self.handle_power_click,
            },  # New power button
        ]

        # Adjust angle range
        total_arc = math.pi * 0.6  # Cover a smaller portion of the arc
        angle_step = total_arc / (len(buttons) - 1)  # Divide arc between buttons
        start_angle = -math.pi / 2 - total_arc / 2  # Start angle for balance

        for i, button_data in enumerate(buttons):
            angle = start_angle + i * angle_step  # Adjusted angle range
            final_x = (
                center.x() + int(radius * math.cos(angle)) - 15
            )  # Final position x
            final_y = (
                center.y() + int(radius * math.sin(angle)) - 12
            )  # Final position y

            button = QPushButton(self)
            button.setIcon(qta.icon(button_data["icon"]))
            button.setStyleSheet(self.button_style())
            button.setFixedSize(25, 25)  # Increase the button size
            button.setIconSize(QSize(20, 20))  # Adjust the icon size

            button.move(
                center.x() - 15, center.y() - 15
            )  # Start at the circle's center
            button.clicked.connect(
                lambda _, b=button, bd=button_data: self.handle_button_click(b, bd)
            )
            button.hide()  # Initially hide all buttons

            self.buttons.append(button)

            # Create animation for button movement
            animation = QPropertyAnimation(button, b"pos")
            animation.setDuration(1100)  # 500 ms animation
            animation.setStartValue(QPoint(center.x() - 15, center.y() - 15))
            animation.setEndValue(QPoint(final_x, final_y))
            animation.setEasingCurve(
                QEasingCurve.Type.OutBounce
            )  # Smooth bounce effect
            self.button_animations.append(animation)

    def handle_button_click(self, button, button_data):
        """Handle button clicks and change icons dynamically."""
        if "handler" in button_data:
            button_data["handler"]()
        if "active_icon" in button_data and self.mic_active:
            button.setIcon(qta.icon(button_data["active_icon"]))
        elif "icon" in button_data:
            button.setIcon(qta.icon(button_data["icon"]))

    def toggle_buttons(self):
        """Toggle the visibility of the buttons with animation."""
        self.buttons_visible = not self.buttons_visible
        for i, button in enumerate(self.buttons):
            if self.buttons_visible:
                button.show()
                self.button_animations[i].start()
            else:
                button.hide()

    def mouseDoubleClickEvent(self, event):
        """Handle double-click events to toggle button visibility."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.toggle_buttons()

    def button_style(self):
        """Return updated button style to resemble the provided design."""
        return """
            QPushButton {
                background-color: rgba(33, 33, 33, 255);  /* Dark background color */
                border: 2px solid rgba(200, 200, 200, 150);  /* Light gray border */
                border-radius: 10px;  /* Rounded square shape */
                color: white;  /* Icon color */
            }
            QPushButton:hover {
                background-color: rgba(50, 50, 50, 255);  /* Slightly lighter background on hover */
                border: 2px solid rgba(255, 255, 255, 200);  /* Brighter border on hover */
            }
            QPushButton:pressed {
                background-color: rgba(70, 70, 70, 255);  /* Darker background on press */
            }
        """

    def handle_mic_click(self):
        """Toggle microphone state and activate/deactivate Jarvis."""
        self.mic_active = not self.mic_active
        if self.mic_active:
            self.assistant.run_in_background()  # Activate Jarvis
        else:
            self.assistant.stop_listening()  # Deactivate Jarvis

        # Update microphone button icon
        mic_button = self.buttons[0]  # Assuming the first button is the mic button
        new_icon = "mdi.microphone" if self.mic_active else "mdi.microphone-off"
        mic_button.setIcon(qta.icon(new_icon))

    def handle_fullscreen_click(self):
        self.app_window.resize(600, 400)
        self.app_window.show()

    def handle_send_click(self):
        print("📨 Send icon clicked")
        if self.input_bar.isVisible():
            self.input_bar.hide()
        else:
            # Position it just below the floating circle
            global_pos = self.mapToGlobal(self.rect().bottomLeft())
            self.input_bar.move(global_pos.x() - 50, global_pos.y() + 10)
            self.input_bar.show()
            self.input_bar.raise_()
            self.input_bar.input_field.setFocus()

    def handle_send_input(self):
        text = self.input_bar.input_field.text().strip()
        if text:
            print(f"📤 Input sent: {text}")
            # You can send it to the main app or chatbot
            self.input_bar.input_field.clear()
            self.input_bar.hide()

    def process_send_message(self):
        text = self.input_bar.text().strip()
        if text:
            print(f"✅ Message entered: {text}")
            self.input_bar.clear()
            self.input_bar.hide()

    def handle_close_click(self):
        self.hide_circle()

    def handle_power_click(self):
        print("Power button clicked! Exiting application.")
        QApplication.quit()

    def hide_circle(self):
        """Emit signal to hide the circle."""
        self.wave_timer.stop()  # Stop animation updates
        self.hide_signal.emit()

    def restore_circle(self):
        """Emit signal to restore the circle."""
        self.restore_signal.emit()

    def _hide_circle(self):
        """Actual hiding logic."""
        if not self.is_minimized:
            self.hide()
            self.is_minimized = True

    def _restore_circle(self):
        """Actual restoring logic."""
        if self.is_minimized:
            self.is_minimized = False
            self.setWindowFlags(
                Qt.WindowType.FramelessWindowHint
                | Qt.WindowType.WindowStaysOnTopHint
                | Qt.WindowType.Tool
            )
            self.show()
            self.activateWindow()
            self.wave_timer.start(30)  # Restart animation updates

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Background circle color
        background_color = QColor(33, 33, 33)
        painter.setBrush(QBrush(background_color))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(30, 30, 90, 90)  # Inner circle for the main widget

        # Flashlight effect
        gradient = QRadialGradient(self.width() // 2, self.height() // 2, 90)
        gradient.setColorAt(0, QColor(255, 255, 255, 50))
        gradient.setColorAt(1, QColor(33, 33, 33, 255))
        painter.setBrush(QBrush(gradient))
        painter.drawEllipse(30, 30, 90, 90)

        # Draw waves inside the circle
        self.draw_waves(painter)

    def draw_waves(self, painter):
        """Draw animated sinusoidal waves inside the circle."""
        wave_color = QColor(200, 200, 200, 150)  # White-grayish waves with transparency
        pen = QPen(wave_color, 2)
        painter.setPen(pen)

        # Clip waves to circle bounds
        painter.setClipRect(30, 30, 90, 90)

        # Wave parameters
        amplitudes = [20, 15, 10]
        wavelengths = [30, 25, 20]
        phases = [0, math.pi / 4, math.pi / 2]

        for i in range(3):
            for x in range(30, 120):
                y = (
                    amplitudes[i]
                    * math.sin(
                        (x / wavelengths[i]) * 2 * math.pi + self.wave_phase + phases[i]
                    )
                    + 75
                )
                painter.drawPoint(x, int(y))

    def update_wave_animation(self):
        """Update the wave animation by changing the phase."""
        self.wave_phase += 0.1
        if self.wave_phase > 2 * math.pi:
            self.wave_phase = 0
        self.update()

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


def check_existing_user():
    """Check if a user is already registered on this machine."""
    LOCAL_STORAGE_FILE = "user_config.json"
    print("Checking for existing user...")  # Debug statement

    if os.path.exists(LOCAL_STORAGE_FILE):
        print(f"Config file found: {LOCAL_STORAGE_FILE}")  # Debug statement
        try:
            with open(LOCAL_STORAGE_FILE, "r") as f:
                data = json.load(f)
                print(f"Config file content: {data}")  # Debug statement
                user_id = data.get("user_id")
                if user_id:  # Ensure the ID is not None or empty
                    print(f"Existing user detected: {user_id}")  # Debug statement
                    return user_id
                else:
                    print("No user_id found in config file.")  # Debug statement
        except json.JSONDecodeError as e:
            print(f"Error reading local storage file: {e}")  # Debug statement
    else:
        print("No config file found.")  # Debug statement

    return None


def launch_main_window():
    """Launch the main window."""
    print("Launching main application...")  # Debug statement
    main_window = MainWindow()
    floating_circle = FloatingCircle(main_window)
    main_window.set_circle_widget(floating_circle)
    # Start reminder checker in background
    user_id = check_existing_user()
    reminder_system = ReminderSystem()
    reminder_system.start_reminder_checker(user_id)

    # Override close behavior to hide instead of closing
    def closeEvent(event):
        event.ignore()
        main_window.hide()

    main_window.closeEvent = closeEvent

    floating_circle.move(200, 200)
    floating_circle.show()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    apply_stylesheet(app, theme="dark_teal.xml")

    # Check if the user is already registered
    from global_tracker import tracker_instance

    tracker_instance.start()  # ✅ Start tracking immediately

    user_id = check_existing_user()
    if user_id:
        print(
            f"User already registered with ID: {user_id}. Launching main application."
        )  # Debug statement
        launch_main_window()  # Launch the main application
    else:
        print(
            "No registered user found. Launching registration wizard."
        )  # Debug statement
        wizard = RegistrationWizard(on_registration_complete=launch_main_window)
        wizard.mainloop()

    sys.exit(app.exec())
