import pyautogui
import time

print("Move your mouse to each field and press Ctrl+C to exit.")
try:
    while True:
        x, y = pyautogui.position()
        print(f"Current Mouse Position: ({x}, {y})", end="\r")
        time.sleep(0.1)
except KeyboardInterrupt:
    print("\nDone.")
