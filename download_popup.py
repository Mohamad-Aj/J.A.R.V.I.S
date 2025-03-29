from PyQt6.QtWidgets import (
    QWidget,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QLineEdit,
    QApplication,
    QHBoxLayout,
    QGraphicsDropShadowEffect,
    QSizePolicy,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
import threading
from playsound import playsound


class FileActionPopup(QWidget):
    def __init__(self, file_name, callback=None):
        super().__init__()
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

        self.file_name = file_name
        self.callback = callback

        self.setWindowTitle("")
        self.setMinimumSize(360, 180)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 180))
        shadow.setOffset(0, 4)
        self.setGraphicsEffect(shadow)

        container = QWidget()
        container.setStyleSheet(
            """
            QWidget {
                background-color: #1e1e1e;
                border-radius: 20px;
            }
        """
        )

        main_layout = QVBoxLayout(container)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(12)

        # === Top Bar with Close Button ===
        top_bar = QHBoxLayout()
        top_bar.setContentsMargins(0, 0, 0, 0)
        top_bar.setSpacing(0)
        top_bar.addStretch()

        btn_close = QPushButton("✕")
        btn_close.setFixedSize(24, 24)
        btn_close.setStyleSheet(
            """
            QPushButton {
                background-color: transparent;
                color: white;
                font-size: 16px;
                border: none;
            }
            QPushButton:hover {
                color: #ff5252;
            }
        """
        )
        btn_close.clicked.connect(self.close)
        top_bar.addWidget(btn_close)
        main_layout.addLayout(top_bar)

        # === Message Label ===
        self.label = QLabel(f"What would you like me to do with '{file_name}'?")
        self.label.setWordWrap(True)
        self.label.setMaximumHeight(60)
        self.label.setStyleSheet(
            """
            QLabel {
                font-size: 16px;
                font-weight: bold;
                color: #ffffff;
            }
        """
        )
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(self.label)

        # === Input Field ===
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText(
            "Type your action (e.g. summarize, archive)..."
        )
        self.input_field.setStyleSheet(
            """
            QLineEdit {
                background-color: #2c2c2c;
                color: white;
                border-radius: 10px;
                padding: 8px;
                font-size: 14px;
                border: 1px solid #555;
            }
        """
        )
        self.feedback_label = QLabel("Default")
        self.feedback_label.setStyleSheet(
            """
            QLabel {
                color: #ff5252;
                font-size: 12px;
            }
        """
        )
        self.feedback_label.setFixedHeight(24)

        self.feedback_label.setWordWrap(True)
        self.feedback_label.setVisible(False)
        self.feedback_label.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        main_layout.addWidget(self.feedback_label)
        main_layout.addWidget(self.input_field)

        # === Submit Button ===
        btn_submit = QPushButton("Submit")
        btn_submit.setStyleSheet(
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
        btn_submit.clicked.connect(self.submit)
        main_layout.addWidget(btn_submit)

        # === Outer Wrapper with masking fix ===
        wrapper = QVBoxLayout(self)
        wrapper.setContentsMargins(0, 0, 0, 0)
        wrapper.addWidget(container)

        # Apply input mask based on the visible container
        self.setMask(container.mask())

        threading.Thread(target=self.play_sound, daemon=True).start()

    def play_sound(self):
        try:
            playsound("alarm.mp3")
        except Exception as e:
            print(f"[Sound Error]: {e}")

    def submit(self):
        from pathlib import Path

        response = self.input_field.text().strip()
        self.feedback_label.clear()
        self.feedback_label.setVisible(False)

        if not response:
            self.feedback_label.setText("⚠️ Please type a command.")
            self.feedback_label.setStyleSheet("color: #ffca28; font-size: 12px;")
            self.feedback_label.setVisible(True)
            return

        if self.callback:
            result = self.callback(self.file_name, response)

            if result is True:
                self.feedback_label.setText("✅ Action completed.")
                self.feedback_label.setStyleSheet("color: #4caf50; font-size: 12px;")

            elif isinstance(result, str):
                path_obj = Path(result)

                if path_obj.exists():
                    # File was moved (e.g., via "put" or "open")
                    self.file_name = str(path_obj)
                    self.label.setText(
                        f"What would you like me to do with '{path_obj.name}'?"
                    )
                    # Decide feedback based on action type
                    if response.startswith("put"):
                        self.feedback_label.setText("✅ File moved.")
                    elif response.startswith("open"):
                        self.feedback_label.setText("✅ File opened successfully.")
                    else:
                        self.feedback_label.setText("✅ Action completed.")

                    self.feedback_label.setStyleSheet(
                        "color: #4caf50; font-size: 12px;"
                    )

                elif result.startswith("✅"):
                    # A direct success message from callback
                    self.feedback_label.setText(result)
                    self.feedback_label.setStyleSheet(
                        "color: #4caf50; font-size: 12px;"
                    )

                else:
                    # It's an error message
                    self.feedback_label.setText(result)
                    self.feedback_label.setStyleSheet(
                        "color: #ff5252; font-size: 12px;"
                    )

            else:
                self.feedback_label.setText("❌ Unsupported action.")
                self.feedback_label.setStyleSheet("color: #ff5252; font-size: 12px;")

            self.feedback_label.setVisible(True)

            self.input_field.clear()

            # 🔧 Fix layout resizing
            self.label.adjustSize()
            self.feedback_label.adjustSize()
            self.layout().activate()
            self.adjustSize()
            self.updateGeometry()
            self.repaint()

            from PyQt6.QtCore import QTimer

            # Hide feedback after 2 seconds
            QTimer.singleShot(1500, lambda: self.feedback_label.setVisible(False))

    def move_to_bottom_right(self):
        screen_geometry = QApplication.primaryScreen().geometry()
        x = screen_geometry.width() - self.width() - 20
        y = screen_geometry.height() - self.height() - 40
        self.move(x, y)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_pos = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton:
            if hasattr(self, "drag_pos"):
                self.move(self.pos() + event.globalPosition().toPoint() - self.drag_pos)
                self.drag_pos = event.globalPosition().toPoint()

    def mouseReleaseEvent(self, event):
        self.drag_pos = None
        self.repaint()
        self.input_field.setFocus()
