from PyQt6.QtCore import QThread, pyqtSignal
import datetime
import psutil
from collections import defaultdict
import win32gui
import win32process


class ScreenTimeWorker(QThread):
    data_ready = pyqtSignal(dict)

    def __init__(self, tracker_instance):
        super().__init__()
        self.tracker = tracker_instance

    def run(self):
        # Run in background
        activity_data = self.tracker.get_activity_data()
        self.data_ready.emit(activity_data)
