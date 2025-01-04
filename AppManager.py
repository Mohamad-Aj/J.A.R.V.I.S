from PyQt6.QtWidgets import QDialog, QListWidget, QListWidgetItem, QWidget,QPushButton, QVBoxLayout, QHBoxLayout, QLabel, QMessageBox
from PyQt6.QtGui import QIcon
from PyQt6.QtCore import Qt, QThread, pyqtSignal
import subprocess
import sys
import qtawesome as qta


class UninstallAppWorker(QThread):
    finished = pyqtSignal(bool, str)  # Emits a signal when done (success or failure)

    finished = pyqtSignal(bool, str)  # Emits a signal when done (success or failure)

    def __init__(self, uninstall_command, parent=None):
        super().__init__(parent)
        self.uninstall_command = uninstall_command

    def run(self):
        try:
            subprocess.run(self.uninstall_command, check=True, shell=True)
            self.finished.emit(True, "The application has been uninstalled successfully.")
        except Exception as e:
            self.finished.emit(False, str(e))

class FetchAppsWorker(QThread):
    apps_fetched = pyqtSignal(list)
    error_occurred = pyqtSignal(str)

    def run(self):
        try:
            apps = self.get_installed_apps()
            self.apps_fetched.emit(apps)
        except Exception as e:
            self.error_occurred.emit(str(e))

    def get_installed_apps(self):
        import winreg

        uninstall_keys = [
            r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall",
            r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall",
        ]
        apps = []

        for hive in [winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER]:
            for key in uninstall_keys:
                try:
                    with winreg.OpenKey(hive, key) as reg_key:
                        for i in range(0, winreg.QueryInfoKey(reg_key)[0]):
                            subkey_name = winreg.EnumKey(reg_key, i)
                            with winreg.OpenKey(reg_key, subkey_name) as subkey:
                                try:
                                    app_name = winreg.QueryValueEx(subkey, "DisplayName")[0]
                                    uninstall_string = winreg.QueryValueEx(subkey, "UninstallString")[0].strip().strip('"')
                                    apps.append((app_name.strip(), uninstall_string.strip()))
                                except FileNotFoundError:
                                    continue
                except FileNotFoundError:
                    continue
        return apps




class ListAppsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Installed Applications")
        self.setFixedSize(500, 400)
        self.setStyleSheet("background-color: #333333; color: white;")

        # Layout
        layout = QVBoxLayout(self)

        self.app_list_widget = QListWidget()
        self.app_list_widget.setStyleSheet("""
            QListWidget {
                background-color: #2e2e2e;
                border: 1px solid #555555;
                padding: 5px;
                border-radius: 5px;
                font-size: 14px;
            }
            QListWidget::item {
                color: white;
            }
        """)
        layout.addWidget(self.app_list_widget)

        # Create a worker thread
        self.worker = FetchAppsWorker()
        self.worker.apps_fetched.connect(self.populate_app_list)
        self.worker.error_occurred.connect(self.handle_error)

        # Fetch and display installed apps
        self.load_installed_apps()

    def load_installed_apps(self):
        
        self.worker.start()

    def populate_app_list(self, installed_apps):
        installed_apps.sort(key=lambda x: x[0].lower())
        for app_name, product_code in installed_apps:
            container = QWidget()
            container_layout = QHBoxLayout(container)
            container_layout.setContentsMargins(5, 5, 5, 5)

            # App name label
            app_label = QLabel(app_name)
            app_label.setStyleSheet("color: white; font-size: 14px;")
            container_layout.addWidget(app_label, alignment=Qt.AlignmentFlag.AlignLeft)

            # Trash button
            bin_button = QPushButton()
            bin_button.setIcon(qta.icon('mdi.trash-can', color='black'))
            bin_button.setStyleSheet("""
                QPushButton {
                    background-color: white;
                    color: black;
                    border: none;
                    border-radius: 5px;
                    padding: 5px;
                }
                QPushButton:hover {
                    background-color: lightgray;
                }
            """)
            bin_button.setFixedSize(40, 20)
            bin_button.clicked.connect(lambda _, code=product_code: self.uninstall_app(code))

            container_layout.addWidget(bin_button, alignment=Qt.AlignmentFlag.AlignRight)

            # Add container to the list widget
            container_item = QListWidgetItem()
            self.app_list_widget.addItem(container_item)
            self.app_list_widget.setItemWidget(container_item, container)



    def uninstall_app(self, uninstall_string):
        confirm = QMessageBox.question(
            self,
            "Confirm Uninstall",
            "Are you sure you want to uninstall this application?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if confirm == QMessageBox.StandardButton.Yes:
            # Proceed with uninstallation
            self.app_list_widget.setDisabled(True)
            if "msiexec" in uninstall_string.lower():
                # Handle MSI-based uninstallation
                self.uninstall_worker = UninstallAppWorker(uninstall_string)
            else:
                # Handle EXE-based uninstallation
                self.uninstall_worker = UninstallAppWorker(f'"{uninstall_string}"')
            
            self.uninstall_worker.finished.connect(self.on_uninstall_finished)
            self.uninstall_worker.start()



    def on_uninstall_finished(self, success, message):
        # Re-enable the list widget
        self.app_list_widget.setDisabled(False)

        if success:
            QMessageBox.information(self, "Success", message)
            self.refresh_app_list()  # Refresh the list after successful uninstallation
        else:
            QMessageBox.critical(self, "Error", f"Failed to uninstall the application.\n\n{message}")
    
    def refresh_app_list(self):
        self.app_list_widget.clear()  # Clear the current list
        self.load_installed_apps()   # Reload the apps





    def handle_error(self, error_message):
        QMessageBox.critical(self, "Error", f"An error occurred:\n\n{error_message}\n\n"
                                            "Possible causes:\n"
                                            "- Missing uninstall information in the registry\n"
                                            "- Insufficient permissions\n"
                                            "- Corrupt uninstallation package.")

