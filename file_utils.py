import os
import psutil
import win32gui
import win32process
from PyQt6.QtCore import QThread, pyqtSignal, Qt
from PyQt6.QtWidgets import (
    QProgressDialog,
    QDialog,
    QVBoxLayout,
    QLabel,
    QTextEdit,
    QMessageBox,
)
from PyQt6.QtGui import QRegion, QPainterPath
from main_window import SummarizeFileWorker
import json

SUGGESTED_FILE_STORE = "suggested_files.json"


def load_suggested_files():
    if os.path.exists(SUGGESTED_FILE_STORE):
        with open(SUGGESTED_FILE_STORE, "r", encoding="utf-8") as f:
            return set(json.load(f))
    return set()


def save_suggested_file(path):
    path = os.path.abspath(path).lower()  # normalize ✅
    print("✅ Saving summarized file:", path)
    suggestions = load_suggested_files()
    suggestions.add(path)
    with open(SUGGESTED_FILE_STORE, "w", encoding="utf-8") as f:
        json.dump(list(suggestions), f, indent=2, ensure_ascii=False)


def get_open_file_paths():
    """
    Detects open windows and extracts file paths from their titles.
    Returns only files that have NOT been previously summarized.
    """
    valid_extensions = [".pdf", ".docx", ".txt"]
    file_paths = set()

    def window_enum_callback(hwnd, _):
        if win32gui.IsWindowVisible(hwnd):
            title = win32gui.GetWindowText(hwnd)
            if any(ext in title.lower() for ext in valid_extensions):
                _, pid = win32process.GetWindowThreadProcessId(hwnd)
                try:
                    proc = psutil.Process(pid)
                    for f in proc.open_files():
                        if f.path.lower().endswith(tuple(valid_extensions)):
                            file_paths.add(f.path)
                except Exception:
                    pass  # Handle access errors, etc.

    win32gui.EnumWindows(window_enum_callback, None)

    # Filter out already suggested (summarized) files
    previously_summarized = load_suggested_files()
    return [f for f in file_paths if f not in previously_summarized]


def detect_open_files_and_summarize(parent):
    paths = get_open_file_paths()
    paths = [
        f for f in paths if os.path.abspath(f).lower() not in load_suggested_files()
    ]

    if not paths:
        return  # ✅ Skip silently if no new files

    dialog = FileSelectionDialog(paths, parent)
    dialog.exec()

    for path in dialog.get_selected_files():
        if os.path.exists(path):
            save_suggested_file(path)
            file_type = path.lower()
            if file_type.endswith(".pdf"):
                file_content = parent.read_pdf(path)
            elif file_type.endswith(".docx"):
                file_content = parent.read_docx(path)
            elif file_type.endswith(".txt"):
                file_content = parent.read_txt(path)
            else:
                continue

            file_content = file_content[:2000]

            progress_dialog = QProgressDialog(
                "Summarizing open file...", None, 0, 0, parent
            )
            progress_dialog.setWindowModality(Qt.WindowModality.ApplicationModal)
            progress_dialog.setAutoClose(False)
            progress_dialog.setAutoReset(False)
            progress_dialog.setWindowFlags(
                progress_dialog.windowFlags() | Qt.WindowType.FramelessWindowHint
            )
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
            radius = 20
            path_mask = QPainterPath()
            path_mask.addRoundedRect(
                0, 0, progress_dialog.width(), progress_dialog.height(), radius, radius
            )
            region = QRegion(path_mask.toFillPolygon().toPolygon())
            progress_dialog.setMask(region)
            progress_dialog.show()

            worker = SummarizeFileWorker(path, file_content, parent)
            worker.finished.connect(
                lambda summary, p=path: parent.show_summary_panel(p, summary)
            )
            worker.error.connect(
                lambda e, p=path: parent.show_summary_panel(p, f"⚠️ Error: {e}")
            )
            worker.finished.connect(progress_dialog.close)
            worker.error.connect(progress_dialog.close)
            worker.start()


from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QLabel,
    QPushButton,
    QHBoxLayout,
    QWidget,
    QScrollArea,
)
from PyQt6.QtCore import Qt
import os


class FileSelectionDialog(QDialog):
    def __init__(self, file_paths, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select Files to Summarize")
        self.selected_files = set()
        self.excluded_files = set()
        self.path_to_buttons = {}

        self.setMinimumSize(600, 400)

        layout = QVBoxLayout()
        layout.addWidget(QLabel("📂 Select files to summarize:"))

        scroll_area = QScrollArea()
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout()

        for path in file_paths:
            file_widget = QWidget()
            file_layout = QHBoxLayout()
            file_label = QLabel(os.path.basename(path))

            include_btn = QPushButton("✔")
            exclude_btn = QPushButton("✖")

            for btn in (include_btn, exclude_btn):
                btn.setFixedWidth(80)
                btn.setStyleSheet(self.get_default_button_style())

            include_btn.clicked.connect(lambda _, p=path: self.toggle_include(p))
            exclude_btn.clicked.connect(lambda _, p=path: self.toggle_exclude(p))

            file_layout.addWidget(file_label)
            file_layout.addStretch()
            file_layout.addWidget(include_btn)
            file_layout.addWidget(exclude_btn)
            file_widget.setLayout(file_layout)

            self.path_to_buttons[path] = (include_btn, exclude_btn)

            scroll_layout.addWidget(file_widget)

        scroll_widget.setLayout(scroll_layout)
        scroll_area.setWidget(scroll_widget)
        scroll_area.setWidgetResizable(True)
        layout.addWidget(scroll_area)

        # Final Send button
        self.send_button = QPushButton("Send")
        self.send_button.setFixedHeight(40)
        self.send_button.setStyleSheet(
            """
            QPushButton {
                background-color: white;
                color: black;
                border: none;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #ccc;
            }
        """
        )
        self.send_button.clicked.connect(self.accept)
        layout.addWidget(self.send_button, alignment=Qt.AlignmentFlag.AlignCenter)

        self.setLayout(layout)

    def get_default_button_style(self):
        return """
            QPushButton {
                background-color: white;
                color: black;
                border: none;
                font-weight: bold;
                font-size: 16px;
            }
            QPushButton:hover {
                background-color: #ddd;
            }
        """

    def get_active_button_style(self, color):
        return f"""
            QPushButton {{
                background-color: {color};
                color: white;
                border: none;
                font-weight: bold;
                font-size: 16px;
            }}
        """

    def get_selected_files(self):
        return list(self.selected_files)

    def toggle_include(self, path):
        include_btn, exclude_btn = self.path_to_buttons[path]

        if path in self.selected_files:
            self.selected_files.remove(path)
            include_btn.setStyleSheet(self.get_default_button_style())
        else:
            self.selected_files.add(path)
            self.excluded_files.discard(path)
            include_btn.setStyleSheet(self.get_active_button_style("#4CAF50"))  # green
            exclude_btn.setStyleSheet(self.get_default_button_style())

    def toggle_exclude(self, path):
        include_btn, exclude_btn = self.path_to_buttons[path]

        if path in self.excluded_files:
            self.excluded_files.remove(path)
            exclude_btn.setStyleSheet(self.get_default_button_style())
        else:
            self.excluded_files.add(path)
            self.selected_files.discard(path)
            exclude_btn.setStyleSheet(self.get_active_button_style("#f44336"))  # red
            include_btn.setStyleSheet(self.get_default_button_style())
