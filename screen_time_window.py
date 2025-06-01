# screen_time_window.py
from PyQt6.QtWidgets import QMainWindow
from activity_GUI import DashboardPanel


class DashboardWindow(QMainWindow):
    def __init__(self, activity_data, tracker_instance):
        super().__init__()
        self.setWindowTitle("📊 System Activity Summary")
        self.setStyleSheet("background-color: #222; color: white;")
        panel = DashboardPanel(activity_data, tracker_instance)
        self.setCentralWidget(panel)
        self.resize(800, 600)
