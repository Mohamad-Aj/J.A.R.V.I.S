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
        self.activity_log = []
        self.total_screen_time = 0
        self.total_idle_time = 0
        self.running = False

    def get_foreground_app(self):
        try:
            hwnd = win32gui.GetForegroundWindow()
            if hwnd == 0:
                return "No Active Window"

            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            if not pid:
                return "No PID"

            process = psutil.Process(pid)
            name = process.name()

            return name or "Unnamed App"
        except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
            print("[TRACKER ERROR] Access issue:", e)
            return "Access Denied"
        except Exception as e:
            print("[TRACKER ERROR] General issue:", e)
            return "Unknown"

    def get_idle_duration(self):
        class LASTINPUTINFO(ctypes.Structure):
            _fields_ = [("cbSize", ctypes.c_uint), ("dwTime", ctypes.c_uint)]

        lii = LASTINPUTINFO()
        lii.cbSize = ctypes.sizeof(LASTINPUTINFO)
        if ctypes.windll.user32.GetLastInputInfo(ctypes.byref(lii)):
            millis = ctypes.windll.kernel32.GetTickCount() - lii.dwTime
            return millis / 1000.0  # convert to seconds
        return 0

    def start(self):
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self._track, daemon=True)
            self.thread.start()

    def _track(self):
        last_app = None
        while self.running:
            idle_secs = self.get_idle_duration()
            app = self.get_foreground_app()
            now = datetime.datetime.now()

            # print(
            #     f"[TRACKER] ⏱️ {now.strftime('%H:%M:%S')} - App: {app} | Idle: {idle_secs:.1f}s"
            # )

            with self.lock:
                if idle_secs < 60:
                    self.total_screen_time += 1
                    self.app_usage[app] += 1
                    if app != last_app:
                        self.activity_log.append((now, app))
                        last_app = app
                else:
                    self.total_idle_time += 1

            time.sleep(1)

    def get_activity_data(self):
        with self.lock:
            return {
                "apps": dict(self.app_usage),
                "total_screen_time": round(self.total_screen_time / 60, 1),
                "idle_time": round(self.total_idle_time / 60, 1),
                "log": list(self.activity_log),
            }

    def get_task_manager_data(self):
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
                        "cpu": info["cpu_percent"],  # May require a delay for accuracy
                        "memory": round(
                            info["memory_info"].rss / (1024 * 1024), 1
                        ),  # in MB
                        "start_time": datetime.datetime.fromtimestamp(
                            info["create_time"]
                        ).strftime("%H:%M:%S"),
                        "uptime": str(
                            datetime.datetime.now()
                            - datetime.datetime.fromtimestamp(info["create_time"])
                        ).split(".")[0],
                    }
                )
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return sorted(
            processes, key=lambda x: x["cpu"], reverse=True
        )  # Sort by CPU usage
