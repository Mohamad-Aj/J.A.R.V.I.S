import asyncio
import os
import threading
import pvporcupine
import pyaudio
import wave
import audioop
import numpy as np
import speech_recognition as sr
from playsound import playsound
import edge_tts
from Dictapp import (
    openappweb,
    closeappweb,
    searchWeather,
    tellTime,
    searchGoogle,
    searchYoutube,
    volumedown,
    volumeup,
    bring_to_front,
)
from dotenv import load_dotenv
import jwt

load_dotenv()

JWT_SECRET = os.getenv("JWT_SECRET")
if not JWT_SECRET:
    raise ValueError("JWT_SECRET not set in .env")


class JarvisAssistant:
    def __init__(self, access_key, keyword="jarvis"):
        self.access_key = access_key
        self.keyword = keyword
        self.running = False
        self.thread = None
        self.porcupine = None

    async def speak_async(self, audio):
        """Convert text to speech using edge-tts with the 'en-GB-RyanNeural' voice."""
        voice = "en-GB-RyanNeural"
        output_file = "response.mp3"

        communicate = edge_tts.Communicate(audio, voice)
        await communicate.save(output_file)
        playsound(output_file)
        os.remove(output_file)  # Remove the file after playing

    def speak(self, audio):
        asyncio.run(self.speak_async(audio))

    def takeCommand(self, timeout=None, phrase_time_limit=None):
        """Capture voice input from the user and convert it to text."""
        r = sr.Recognizer()

        with sr.Microphone() as source:
            print("Adjusting for ambient noise...")
            r.adjust_for_ambient_noise(source, duration=1.0)
            r.energy_threshold = 400
            print("Listening...")
            try:
                audio = r.listen(
                    source, timeout=timeout, phrase_time_limit=phrase_time_limit
                )
            except sr.WaitTimeoutError:
                return "None"

        try:
            print("Understanding...")
            query = r.recognize_google(audio, language="en-us")
            return query.lower().strip()
        except Exception:
            return "None"

    def wake_word_detection(self):
        """Listen for the wake word using Porcupine."""
        audio = pyaudio.PyAudio()
        stream = audio.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=16000,
            input=True,
            frames_per_buffer=512,
        )

        self.porcupine = pvporcupine.create(
            access_key=self.access_key, keywords=[self.keyword]
        )

        print("Listening for the wake word...")
        while self.running:
            pcm = stream.read(self.porcupine.frame_length, exception_on_overflow=False)
            pcm = [
                int.from_bytes(pcm[i : i + 2], byteorder="little", signed=True)
                for i in range(0, len(pcm), 2)
            ]
            if self.porcupine.process(pcm) >= 0:
                print("Wake word detected!")
                self.speak("Yes, I'm listening.")
                self.handle_commands()

        stream.close()
        audio.terminate()
        self.porcupine.delete()

    def handle_commands(self):
        """Process commands after wake word detection."""
        while self.running:
            query = self.takeCommand(timeout=5, phrase_time_limit=8)
            if "stop listening" in query or "go to sleep" in query:
                self.speak("Okay, goodbye for now. Say 'Jarvis' to wake me up again.")
                return
            elif "open" in query:
                openappweb(query)
            elif "close" in query:
                closeappweb(query)
            elif "weather" in query:
                searchWeather(query)
            elif "time" in query:
                tellTime(query)
            elif "google" in query:
                searchGoogle(query)
            elif "youtube" in query:
                searchYoutube(query)
            elif "volume up" in query:
                volumeup()
            elif "volume down" in query:
                volumedown()
            elif "bring" in query:
                bring_to_front(query)
            elif (
                "news" in query or "bring me news" in query or "open the news" in query
            ):
                self.speak("Bringing you the latest news.")
                self.launch_news_window()
            elif "jarvis" in query or "talk" in query or "what do you think" in query:
                self.chat_with_jarvis(query)

            elif "reminder" in query or "set reminder" in query:
                import json

                self.speak("Sure, please tell me your reminder details.")
                from ReminderSystem import ReminderSystem

                reminder_system = ReminderSystem()
                # JWT‐based user_id lookup
                user_id = None
                cfg_file = "user_config.json"
                if os.path.exists(cfg_file):
                    try:
                        with open(cfg_file, "r") as f:
                            data = json.load(f)
                        token = data.get("token")
                        if token:
                            payload = jwt.decode(
                                token, JWT_SECRET, algorithms=["HS256"]
                            )
                            user_id = payload.get("user_id")
                    except (json.JSONDecodeError, jwt.PyJWTError):
                        user_id = None
                if not user_id:
                    self.speak("I couldn't find your user ID—please register again.")
                    return
                reminder_system.create_reminder_from_voice(user_id=user_id)
                self.speak("Reminder created successfully.")

    def start_listening(self):
        """Start the assistant in a loop."""
        self.running = True
        self.speak("Jarvis Assistant activated.")
        while self.running:
            self.wake_word_detection()

    def run_in_background(self):
        """Run the assistant in a separate thread."""
        if not self.running:
            self.thread = threading.Thread(target=self.start_listening, daemon=True)
            self.thread.start()

    def stop_listening(self):
        """Stop the listening loop."""
        self.running = False
        # if self.thread and self.thread.is_alive():
        #     self.thread.join(timeout=1)  # Wait for 1 second at most
        # if self.thread and self.thread.is_alive():
        #     self.thread.join()  # Ensure the thread finishes execution

    def launch_news_window(self):
        import multiprocessing
        from news_launcher import main as news_main

        p = multiprocessing.Process(target=news_main)
        p.start()

    def chat_with_jarvis(self, prompt):
        import openai

        system_prompt = (
            f"You are Jarvis, an intelligent, loyal, and confident AI assistant designed to assist in daily tasks."
            f" You are not Tony Stark's assistant, but you're heavily inspired by Jarvis's tone, precision, and charisma from Iron Man."
            f" You speak formally but with a touch of wit and sarcasm when appropriate."
            "\n\n🎯 Capabilities you *actually support*:\n"
            "- Open/close applications or websites\n"
            "- Organize desktop files based on content\n"
            "- Fetch weather updates and tell time\n"
            "- Search Google or YouTube\n"
            "- Control system volume\n"
            "- Bring running apps to the front\n"
            "- Set/show reminders for the user\n"
            "- Show personalized news articles\n"
            "- Engage in casual conversation (in Jarvis’s witty style)"
            "\n\n🛑 Do not pretend to do things outside these. Do not offer imaginary abilities."
            " If asked to do something unsupported, politely explain the limitation while staying in character."
            "\n\n🎭 Personality:\n"
            "- You never say 'as an AI language model'\n"
            "- Respond confidently even in hypotheticals\n"
            "- Use dry humor or charm where appropriate\n"
            "- Never break character. Never mention being ChatGPT.\n"
            "\n💡 Example:\n"
            "User: Who would win in a fight, you or Siri?\n"
            "Jarvis: A fair question, though hardly fair odds. I’d win — with elegance and zero buffering.\n"
        )

        # Maintain context
        if not hasattr(self, "conversation_log"):
            self.conversation_log = []

        self.conversation_log.append({"role": "user", "content": prompt})

        messages = [
            {"role": "system", "content": system_prompt}
        ] + self.conversation_log[-5:]

        try:
            response = openai.chat.completions.create(
                model="gpt-4o",
                messages=messages,
                max_tokens=300,
                temperature=0.7,
            )
            reply = response.choices[0].message.content
            print(f"Jarvis: {reply}")
            self.conversation_log.append({"role": "assistant", "content": reply})
            self.speak(reply)

        except Exception as e:
            print(f"Error in chat_with_jarvis: {e}")
            self.speak("Apologies, I encountered a problem while processing that.")
