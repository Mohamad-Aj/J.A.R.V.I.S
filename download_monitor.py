import os
import time
import threading
from collections import defaultdict
from pathlib import Path

# from download_popup import


class DownloadMonitor:
    def __init__(
        self,
        downloads_path=None,
        scan_interval=10,
        frequency_threshold=1,
        popup_callback=None,
    ):
        self.downloads_path = Path(downloads_path or Path.home() / "Downloads")
        self.scan_interval = scan_interval
        self.frequency_threshold = frequency_threshold
        self.file_types = [".pdf", ".zip", ".docx", ".csv", ".xlsx"]

        self.file_type_counts = defaultdict(int)  # Tracks total frequency per extension
        self.file_counts = defaultdict(int)  # Tracks per-file count (used for new ones)
        self.seen_files = set()
        self.running = False
        self.popup_callback = popup_callback  # NEW

    def start(self):
        # Analyze existing files to learn frequency
        for file in self.downloads_path.glob("*"):
            ext = file.suffix.lower()
            if ext in self.file_types:
                self.seen_files.add(file.name)
                self.file_type_counts[ext] += 1

        self.running = True
        threading.Thread(target=self.monitor_loop, daemon=True).start()

    def stop(self):
        self.running = False

    def monitor_loop(self):
        while self.running:
            self.scan_folder()
            time.sleep(self.scan_interval)

    def scan_folder(self):
        current_files = list(self.downloads_path.glob("*"))
        for file in current_files:
            ext = file.suffix.lower()
            if ext in self.file_types and file.name not in self.seen_files:
                self.seen_files.add(file.name)
                self.file_counts[file.name] += 1
                self.file_type_counts[ext] += 1  # Update global type frequency
                if self.file_counts[file.name] == self.frequency_threshold:
                    self.handle_frequent_file(file)

    def handle_frequent_file(self, file_path: Path):
        suggestion = self.suggest_action(file_path)
        print(f"[JARVIS] New download detected: {file_path.name}")
        print(f"[JARVIS] Suggestion: {suggestion}")

        # Trigger popup
        if self.popup_callback:
            self.popup_callback(file_path.name)

    def suggest_action(self, file_path: Path):
        ext = file_path.suffix.lower()
        freq = self.file_type_counts[ext]
        if ext in [".pdf", ".docx"]:
            return f"I've seen a lot of {ext} files lately – want to summarize or archive this?"
        elif ext == ".zip":
            return "Another ZIP – should I extract and organize it?"
        elif ext in [".csv", ".xlsx"]:
            return "New data file – want to analyze or move it to your data folder?"
        return "New file detected – no suggestion available yet."

    def notify_user(self, file_name, suggestion):
        print(f"[JARVIS] New download detected: {file_name}")
        print(f"[JARVIS] Suggestion: {suggestion}")


# if __name__ == "__main__":
#     monitor = DownloadMonitor()
#     monitor.start()
#     print("Monitoring Downloads folder... Press Ctrl+C to stop.")
#     try:
#         while True:
#             time.sleep(1)
#     except KeyboardInterrupt:
#         monitor.stop()
#         print("Stopped monitoring.")


# start_download_monitor.py
