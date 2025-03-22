# process_suggest.py

import time
import win32gui
import win32process
import psutil
from datetime import datetime, timedelta
import threading
from multiprocessing import Process
from idle_popup import launch_idle_popup

app_last_active = {}


def is_window_visible_and_named(hwnd):
    return win32gui.IsWindowVisible(hwnd) and win32gui.GetWindowText(hwnd)


def get_open_window_processes():
    open_apps = {}

    def callback(hwnd, _):
        if is_window_visible_and_named(hwnd):
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            try:
                proc = psutil.Process(pid)
                open_apps[pid] = {
                    "name": proc.name(),
                    "title": win32gui.GetWindowText(hwnd),
                    "hwnd": hwnd,
                }
            except:
                pass

    win32gui.EnumWindows(callback, None)
    return open_apps


def get_active_pid():
    try:
        hwnd = win32gui.GetForegroundWindow()
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        return pid
    except:
        return None


def update_active_and_open_apps():
    while True:
        open_windows = get_open_window_processes()
        active_pid = get_active_pid()
        now = datetime.now()

        for pid, info in open_windows.items():
            if pid not in app_last_active:
                app_last_active[pid] = {
                    "name": info["name"],
                    "title": info["title"],
                    "last_active": datetime.min,
                }

            if pid == active_pid:
                app_last_active[pid]["last_active"] = now

        time.sleep(5)


last_popup_process = None


def check_idle_apps():
    while True:
        now = datetime.now()
        idle_apps = {}

        for pid, info in list(app_last_active.items()):
            if not psutil.pid_exists(pid):
                continue
            idle_time = now - info["last_active"]
            if idle_time > timedelta(minutes=60):  # for testing
                idle_apps[pid] = info

        if idle_apps:
            print(f"[DEBUG] Launching popup process with {len(idle_apps)} idle apps")
            # Use multiprocessing to run the popup independently
            global last_popup_process

            # Terminate previous popup if it exists and is alive
            if last_popup_process and last_popup_process.is_alive():
                print("[DEBUG] Terminating previous popup...")
                last_popup_process.terminate()
                last_popup_process.join()

            # Start new popup
            popup_proc = Process(target=launch_idle_popup, args=(idle_apps,))
            popup_proc.start()
            last_popup_process = popup_proc

        time.sleep(1800)


def start_idle_tracking(ui_context=None):
    threading.Thread(target=update_active_and_open_apps, daemon=True).start()
    threading.Thread(target=check_idle_apps, daemon=True).start()
    print("[DEBUG] Idle tracking started.")
