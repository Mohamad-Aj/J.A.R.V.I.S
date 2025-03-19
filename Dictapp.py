import os
import pyautogui
import webbrowser
import pyttsx3
from playsound import playsound
import datetime
import edge_tts
import asyncio
import psutil
import pygetwindow as gw
import requests
from bs4 import BeautifulSoup
from pynput.keyboard import Key, Controller
from keyboard import send


async def speak_async(audio):
    """Convert text to speech using edge-tts with the 'en-GB-RyanNeural' voice."""
    voice = "en-GB-RyanNeural"
    output_file = "response.mp3"

    communicate = edge_tts.Communicate(audio, voice)
    await communicate.save(output_file)
    playsound(output_file)
    os.remove(output_file)  # Remove the file after playing


def speak(audio):
    asyncio.run(speak_async(audio))


dictapp = {
    "command prompt": "cmd",
    "cmd": "cmd",
    "word": "winword",
    "excel": "excel",
    "chrome": "chrome",
    "vscode": "code",
    "vs code": "code",
    "powerpoint": "powerpnt",
    "whatsapp": "WhatsApp",
    "spotify": "Spotify",
    "discord": "discord",
}

webapps = {
    "instagram": "www.instagram.com",
    "facebook": "www.facebook.com",
    "youtube": "www.youtube.com",
    "gpt": "www.chatgpt.com",
    "twitter": "www.x.com",
    "google": "www.google.com",
    "sami moodle": "moodle.sce.ac.il",
    "sami modle": "moodle.sce.ac.il",
    "sami model": "moodle.sce.ac.il",
    "sami": "moodle.sce.ac.il",
}


def openappweb(query):
    web_keys = list(webapps.keys())
    for web_key in web_keys:
        if web_key in query:
            webbrowser.open(f"https://{webapps[web_key]}")
            speak("Opened Sir")
            return

    app_keys = list(dictapp.keys())
    for app in app_keys:
        if app in query:
            if app == "whatsapp" or app == "spotify" or app == "discord":
                os.system(f"start {dictapp[app]}:")
            else:
                os.system(f"start {dictapp[app]}")
            speak("Opened Sir")
            return
    if query == "coding mode":
        os.system(f"start code")
        webbrowser.open(f"https://www.chatgpt.com")
        speak("Coding Mode Activated Sir")


def is_chrome_running():
    """Check if Chrome is running."""
    for proc in psutil.process_iter(["name"]):
        if "chrome" in proc.info["name"].lower():
            return True
    return False


def bring_chrome_to_foreground():
    """Bring Chrome to the foreground if it's running."""
    # Check if Chrome is currently active
    active_window = gw.getActiveWindow()
    if active_window and "Chrome" in active_window.title:
        return True

    # Use alt-tab to cycle through windows and bring Chrome to the foreground
    for _ in range(5):  # Cycle through the first 5 windows
        pyautogui.hotkey("alt", "tab")
        pyautogui.sleep(0.5)
        active_window = gw.getActiveWindow()
        if active_window and "Chrome" in active_window.title:
            return True

    # Use pygetwindow to directly activate Chrome if found
    try:
        chrome_windows = [
            window
            for window in gw.getWindowsWithTitle("Chrome")
            if "Chrome" in window.title
        ]

        if chrome_windows:
            chrome_window = chrome_windows[0]
            chrome_window.activate()  # Bring the first Chrome window to the foreground
            return True
        else:
            return False
    except gw.PyGetWindowException as e:
        print(f"Failed to activate Chrome window: {e}")
        return False


def closeappweb(query):
    if (
        "one tab" in query
        or "1 tab" in query
        or "two tabs" in query
        or "2 tabs" in query
        or "three tab" in query
        or "3 tabs" in query
        or "four tab" in query
        or "4 tabs" in query
        or "all" in query
    ):
        if is_chrome_running():
            bring_chrome_to_foreground()  # Bring Chrome to the foreground only if it's running

            if "one tab" in query or "1 tab" in query:
                pyautogui.hotkey("ctrl", "w")
                speak("tab closed")
            elif "two tabs" in query or "2 tabs" in query:
                pyautogui.hotkey("ctrl", "w")
                pyautogui.hotkey("ctrl", "w")
                speak("tabs closed")
            elif "three tab" in query or "3 tabs" in query:
                pyautogui.hotkey("ctrl", "w")
                pyautogui.hotkey("ctrl", "w")
                pyautogui.hotkey("ctrl", "w")
                speak("tabs closed")
            elif "four tab" in query or "4 tabs" in query:
                pyautogui.hotkey("ctrl", "w")
                pyautogui.hotkey("ctrl", "w")
                pyautogui.hotkey("ctrl", "w")
                pyautogui.hotkey("ctrl", "w")
                speak("tabs closed")
            elif "all" in query:
                pyautogui.hotkey("alt", "F4")
                speak("app closed")
        else:
            speak("Chrome is not running, Sir")

    else:
        app_keys = list(dictapp.keys())
        for app in app_keys:
            if app in query:
                os.system(f"taskkill /f /im {dictapp[app]}.exe")
                speak("Closed Sir")
                return


def searchWeather(query):

    if "temperature" in query:
        query = query.replace("jarvis", "")
        query = query.replace("for me", "")

        try:
            search_url = f"https://www.google.com/search?q={query}"

            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }
            r = requests.get(search_url, headers=headers)
            data = BeautifulSoup(r.text, "html.parser")
            temp = data.find("span", class_="wob_t q8U8x").text

            # webbrowser.open(search_url)
            speak(f"Current Weather is {temp}")
        except:
            speak("Couldn't find anything related to your topic sir")

    elif "weather" in query:

        query = query.replace("jarvis", "")
        query = query.replace("for me", "")

        try:
            search_url = f"https://www.google.com/search?q={query}"

            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }
            r = requests.get(search_url, headers=headers)
            data = BeautifulSoup(r.text, "html.parser")
            temp = data.find("span", class_="wob_t q8U8x").text

            # webbrowser.open(search_url)
            speak(f"Current Weather is {temp}")
        except:
            speak("Couldn't find anything related to your topic sir")


def tellTime(query):
    if "time" in query or "what time" in query or "the time" in query:
        strTime = datetime.datetime.now().strftime("%H:%M")
        speak(f"The time is {strTime}")


def searchGoogle(query):
    if "google" in query:
        query = query.replace("jarvis", "")
        query = query.replace("on google", "")
        query = query.replace("google search", "")
        query = query.replace("google", "")

        try:
            search_url = f"https://www.google.com/search?q={query}"
            webbrowser.open(search_url)
            speak("Here are the search results on Google, Sir.")
        except:
            speak("Couldn't find anything related to your topic sir")


def searchYoutube(query):
    if "youtube" in query:
        query = query.replace("jarvis", "")
        query = query.replace("youtube search", "")
        query = query.replace("on youtube", "")
        query = query.replace("look up", "")
        query = query.replace("look for", "")
        query = query.replace("youtube", "")

    try:
        web = "https://www.youtube.com/results?search_query=" + query
        webbrowser.open(web)
        speak("Done, Sir")
    except:
        speak("Couldn't find anything related to your topic sir")


keyboard = Controller()


def volumeup():
    for i in range(5):
        keyboard.press(Key.media_volume_up)
        keyboard.release(Key.media_volume_up)


def volumedown():
    for i in range(5):
        keyboard.press(Key.media_volume_down)
        keyboard.release(Key.media_volume_down)


import pygetwindow as gw
import pyautogui


def bring_to_front(query):
    app = None
    for app_name, process_name in dictapp.items():
        if app_name in query:
            app = process_name
            break  # Exit the loop once a match is found

    if not app:  # If no app was matched
        speak("I couldn't find the application in my list, Sir.")
        return False

    """Bring a specific application window to the foreground with voice feedback."""
    windows = gw.getWindowsWithTitle(app)
    if windows:
        window = windows[0]
        if window.isMinimized:
            window.restore()  # Restore the window if it is minimized
        window.activate()  # Activate (bring to foreground)
        # pyautogui.hotkey("win", "up")  # Maximize the window

        speak(f"{app} is now on the screen, Sir.")
        return True
    else:
        speak(f"Could not find {app} running, Sir.")
        return False
