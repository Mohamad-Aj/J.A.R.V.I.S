# activity_tracker.py
import threading
import datetime
import time
import psutil
import win32gui
import ctypes
from collections import defaultdict
import win32process


class ActivityTracker:
    def __init__(self):
        self.lock = threading.Lock()
        self.app_usage = defaultdict(float)
        # Will hold tuples of (timestamp: datetime, app_name: str)
        self.activity_log = []
        self.total_screen_time = 0
        self.total_idle_time = 0
        self.running = False

    def get_foreground_app(self):
        """
        Return the name of the currently active window's process.
        """
        try:
            hwnd = win32gui.GetForegroundWindow()
            if hwnd == 0:
                return "No Active Window"

            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            if not pid:
                return "No PID"

            proc = psutil.Process(pid)
            return proc.name() or "Unnamed App"
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return "Access Denied"
        except Exception:
            return "Unknown"

    def get_idle_duration(self):
        """
        Returns the number of seconds since last user input.
        """

        class LASTINPUTINFO(ctypes.Structure):
            _fields_ = [("cbSize", ctypes.c_uint), ("dwTime", ctypes.c_uint)]

        lii = LASTINPUTINFO()
        lii.cbSize = ctypes.sizeof(LASTINPUTINFO)
        if ctypes.windll.user32.GetLastInputInfo(ctypes.byref(lii)):
            millis = ctypes.windll.kernel32.GetTickCount() - lii.dwTime
            return millis / 1000.0
        return 0

    def start(self):
        """
        Start the background tracking thread.
        """
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self._track, daemon=True)
            self.thread.start()

    def stop(self):
        """
        Stop tracking.
        """
        self.running = False
        if hasattr(self, "thread"):
            self.thread.join()

    def _track(self):
        """
        Internal loop: every second, check idle time. If user is active,
        count it as screen-on, record the timestamp + app name.
        Otherwise, record idle time.
        """
        while self.running:
            idle_secs = self.get_idle_duration()
            now = datetime.datetime.now()
            with self.lock:
                if idle_secs < 60:
                    # Count one more second of screen-on
                    self.total_screen_time += 1
                    # Track per-app usage for pie chart
                    app = self.get_foreground_app()
                    self.app_usage[app] += 1
                    # Log each second of activity for the bar chart
                    self.activity_log.append((now, app))
                else:
                    self.total_idle_time += 1
            time.sleep(1)

    def get_activity_data(self):
        """
        Returns a snapshot of activity data:
          - apps: dict of {app_name: seconds_active}
          - total_screen_time: minutes of active use
          - idle_time: minutes of idle time
          - log: list of (timestamp, app_name) tuples
        """
        with self.lock:
            return {
                "apps": dict(self.app_usage),
                "total_screen_time": round(self.total_screen_time / 60, 1),
                "idle_time": round(self.total_idle_time / 60, 1),
                "log": list(self.activity_log),
            }

    def get_task_manager_data(self):
        """
        Returns a list of process stats for the live task manager.
        """
        processes = []
        for proc in psutil.process_iter(
            ["pid", "name", "cpu_percent", "memory_info", "create_time"]
        ):
            try:
                info = proc.info
                processes.append(
                    {
                        "pid": info["pid"],
                        "name": info["name"],
                        "cpu": info["cpu_percent"],
                        "memory": round(info["memory_info"].rss / (1024 * 1024), 1),
                        "uptime": str(
                            datetime.datetime.now()
                            - datetime.datetime.fromtimestamp(info["create_time"])
                        ).split(".")[0],
                    }
                )
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return sorted(processes, key=lambda x: x["cpu"], reverse=True)
