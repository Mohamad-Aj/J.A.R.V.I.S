# popup_process.py
from PyQt6.QtWidgets import QApplication
import sys
from popup_launcher import ReminderPopup


def launch_popup(title="💧 Time to take a break or drink water!"):
    app = QApplication(sys.argv)
    popup = ReminderPopup(title, None, None)
    popup.show()
    popup.move_to_bottom_right()
    sys.exit(app.exec())
