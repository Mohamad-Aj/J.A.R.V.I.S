# monitor_launcher.py

import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer
from download_popup import FileActionPopup
from download_monitor import DownloadMonitor
import os
import shutil
import subprocess
from pathlib import Path
from PyQt6.QtCore import QObject, pyqtSignal
from csv_summary_popup import FileSummaryPopup  # Adjust the filename if different


# from FileActionPopup import FileActionPopup
active_csv_popups = []


class PopupManager(QObject):
    trigger_popup = pyqtSignal(str)

    def __init__(self, handle_response_func):
        super().__init__()
        self.trigger_popup.connect(self.show_popup)
        self.handle_response_func = handle_response_func
        self.popups = []  # Store popups to prevent GC

    def show_popup(self, file_name):
        popup = FileActionPopup(file_name, callback=self.handle_response_func)
        popup.show()
        popup.move_to_bottom_right()
        self.popups.append(popup)  # Keep reference alive


def handle_user_action(file_name, user_response):
    print(f"[JARVIS] User selected action for {file_name}: {user_response}")
    file_path = Path(file_name)
    if not file_path.exists():
        search_locations = [
            Path.home() / "Downloads",
            Path.home() / "Desktop",
            Path.home() / "Desktop" / "Jarvis_Projects" / "Documents",
        ]
        for loc in search_locations:
            candidate = loc / file_path.name
            if candidate.exists():
                file_path = candidate
                break

    ext = file_path.suffix.lower()

    try:
        if ext == ".zip":
            return handle_zip_action(file_path, user_response.lower().strip())
        elif ext in [".csv", ".xlsx", ".pdf", ".docx"]:
            return handle_document_action(file_path, user_response.lower().strip())
        else:
            print("[JARVIS] Action handling for this file type is not implemented yet.")
            return False
    except Exception as e:
        print(f"[JARVIS] ❌ Unexpected error: {e}")
        return False


def handle_zip_action(file_path: Path, user_input: str):
    valid_extract = {"extract", "unzip", "open", "open folder"}
    valid_vscode = {"vscode", "open in vscode", "code"}

    # Define target extract location
    jarvis_folder = Path.home() / "Desktop" / "Jarvis_Projects"
    extracted_dir = jarvis_folder / file_path.stem

    # Create target folder
    jarvis_folder.mkdir(parents=True, exist_ok=True)

    # Extract if needed
    def extract_zip():
        if not extracted_dir.exists():
            shutil.unpack_archive(str(file_path), str(extracted_dir))
            print(f"[JARVIS] Extracted to: {extracted_dir}")
        else:
            print(f"[JARVIS] Already extracted to: {extracted_dir}")
        file_path.unlink(missing_ok=True)  # Delete original zip

    if user_input in valid_extract:
        extract_zip()
        # Open folder
        if os.name == "nt":  # Windows
            os.startfile(str(extracted_dir))
        else:
            subprocess.run(["xdg-open", str(extracted_dir)])

    elif user_input in valid_vscode:
        extract_zip()
        subprocess.run(
            ["code", str(extracted_dir)], shell=True
        )  # shell=True for Windows

    else:
        print("[JARVIS] ❌ Unsupported action for ZIP files.")


def handle_document_action(file_path: Path, user_input: str):
    jarvis_docs_folder = Path.home() / "Desktop" / "Jarvis_Projects" / "Documents"
    file_name = file_path.name
    target_path = jarvis_docs_folder / file_name

    valid_vscode = {"vscode", "open in vscode", "code"}

    if user_input.startswith("put "):
        dest_input = user_input[4:].strip().strip('"').lower()

        desktop_path = Path.home() / "Desktop"
        if dest_input == "desktop":
            dest_path = desktop_path
        else:
            dest_path = desktop_path / dest_input

        try:
            dest_path.mkdir(parents=True, exist_ok=True)
            final_path = dest_path / file_name
            shutil.move(str(file_path), str(final_path))

            if final_path.exists():
                print(f"[JARVIS] Moved {file_name} to {dest_path}")
                return str(final_path)
            else:
                return "❌ Move failed — target file not found after moving."

        except Exception as e:
            print(f"[JARVIS] ❌ Could not move to {dest_path}: {e}")
            return str(final_path)

    elif user_input in {"open", "open file"}:

        try:
            if not file_path.exists():
                return "❌ File not found. Please check if it was moved."

            os.startfile(str(file_path))  # Just open without touching location
            return str(file_path)  # ✅ still return path so popup updates cleanly
        except Exception as e:
            return f"⚠️ I couldn't open the file. {e}"

    elif user_input in valid_vscode:
        jarvis_docs_folder.mkdir(parents=True, exist_ok=True)
        shutil.move(str(file_path), str(target_path))
        subprocess.run(["code", str(target_path)], shell=True)

    elif user_input == "summarize":
        show_csv_summary_popup(str(file_path))  # works for both csv and pdf
        return "✅ File Summary is Ready"

    else:
        print("[JARVIS] ❌ Unsupported action for this file type.")


def show_csv_summary_popup(file_path: str):
    def launch():
        popup = FileSummaryPopup(file_path)
        popup.show()
        active_csv_popups.append(popup)  # Keep reference alive

    QTimer.singleShot(0, launch)


def start_monitor():
    import sys
    from PyQt6.QtWidgets import QApplication, QWidget
    from PyQt6.QtCore import QTimer, Qt

    from download_launcher import handle_user_action, PopupManager
    from download_monitor import DownloadMonitor

    app = QApplication(sys.argv)

    # Create popup manager and monitor
    popup_manager = PopupManager(handle_user_action)
    monitor = DownloadMonitor(popup_callback=popup_manager.trigger_popup.emit)
    monitor.start()

    print("[JARVIS] ✅ Download monitor loop running...")

    # 🧩 Add a hidden dummy widget to keep the Qt event loop alive
    dummy = QWidget()
    dummy.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen)
    dummy.show()

    sys.exit(app.exec())
