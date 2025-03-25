from PyQt6.QtWidgets import (
    QApplication,
    QWidget,
    QVBoxLayout,
    QLabel,
    QPushButton,
    QHBoxLayout,
    QScrollArea,
    QMessageBox,
    QSizePolicy,
)
from PyQt6.QtCore import Qt, QPoint
import sys
import psutil


class IdleAppPopup(QWidget):
    def __init__(self, idle_apps: dict):
        super().__init__()
        self.setWindowTitle("Idle Apps")
        self.setFixedSize(500, 400)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self.dragging = False
        self.offset = QPoint()

        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ========== Title Bar ==========
        title_bar = QWidget()
        title_bar.setStyleSheet(
            """
            background-color: #222;
            border-top-left-radius: 24px;
            border-top-right-radius: 24px;
        """
        )
        title_layout = QHBoxLayout(title_bar)
        title_layout.setContentsMargins(16, 10, 16, 10)

        title_label = QLabel("🕒 These apps have been idle for a while:")
        title_label.setStyleSheet("font-size: 16px; font-weight: bold; color: white;")
        title_label.setWordWrap(True)

        minimize_btn = QPushButton("⤵")
        minimize_btn.setFixedSize(28, 28)
        minimize_btn.setStyleSheet(
            """
            QPushButton {
                background-color: transparent;
                color: white;
                font-size: 18px;
                border: none;
            }
            QPushButton:hover {
                background-color: #333;
                border-radius: 6px;
            }
        """
        )
        minimize_btn.clicked.connect(self.showMinimized)

        title_layout.addWidget(title_label)
        title_layout.addStretch()
        title_layout.addWidget(minimize_btn)

        main_layout.addWidget(title_bar)

        # ========== Scroll Area for App List ==========
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("border: none;")

        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setSpacing(8)
        content_layout.setContentsMargins(16, 16, 16, 16)

        self.app_rows = {}

        for pid, app in idle_apps.items():
            row_widget = QWidget()
            row_layout = QHBoxLayout(row_widget)
            row_layout.setContentsMargins(5, 5, 5, 5)
            row_layout.setSpacing(10)

            label = QLabel(f"{app['title']} ({app['name']})")
            label.setStyleSheet("color: white;")
            label.setWordWrap(True)
            label.setSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
            )
            label.setMaximumWidth(380)

            close_btn = QPushButton("❌")
            close_btn.setFixedSize(30, 30)
            close_btn.setStyleSheet(
                """
                QPushButton {
                    background-color: transparent;
                    color: white;
                    font-size: 16px;
                    border: none;
                }
                QPushButton:hover {
                    background-color: #222;
                    border-radius: 6px;
                }
            """
            )
            close_btn.clicked.connect(
                lambda _, p=pid, r=row_widget: self.terminate_app(p, r)
            )

            row_layout.addWidget(label)
            row_layout.addStretch()
            row_layout.addWidget(close_btn)

            content_layout.addWidget(row_widget)
            self.app_rows[pid] = row_widget

        scroll_area.setWidget(content_widget)
        main_layout.addWidget(scroll_area)

        # ========== Bottom Area with Dismiss Button ==========
        bottom_bar = QWidget()
        bottom_bar.setStyleSheet(
            """
            background-color: #2c2c2c;
            border-bottom-left-radius: 24px;
            border-bottom-right-radius: 24px;
        """
        )
        bottom_layout = QVBoxLayout(bottom_bar)
        bottom_layout.setContentsMargins(20, 10, 20, 10)

        dismiss_btn = QPushButton("Dismiss")
        dismiss_btn.setStyleSheet(
            """
            QPushButton {
                background-color: #444;
                color: white;
                padding: 8px 16px;
                border-radius: 8px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #666;
            }
        """
        )
        dismiss_btn.clicked.connect(self.close)
        bottom_layout.addWidget(dismiss_btn)
        main_layout.addWidget(bottom_bar)

        # Set global background color
        self.setStyleSheet(
            """
            QWidget#IdleAppPopup {
                background-color: transparent;
            }
            QScrollArea {
                border: none;
            }
        """
        )

    def terminate_app(self, pid, row_widget):
        try:
            psutil.Process(pid).terminate()
            row_widget.setStyleSheet("background-color: rgba(255,0,0,40);")
            for child in row_widget.findChildren(QPushButton):
                child.setDisabled(True)
            for child in row_widget.findChildren(QLabel):
                child.setText(child.text() + " [Closed]")
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to close app: {e}")

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


# Launcher for multiprocessing
def launch_idle_popup(idle_apps):
    app = QApplication(sys.argv)
    popup = IdleAppPopup(idle_apps)
    popup.setObjectName("IdleAppPopup")
    popup.move(800, 400)
    popup.show()
    sys.exit(app.exec())
