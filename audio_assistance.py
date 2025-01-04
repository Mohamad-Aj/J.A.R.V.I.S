import asyncio
import os
import threading
import pvporcupine
import pyaudio
import speech_recognition as sr
from playsound import playsound
import edge_tts
from Dictapp import openappweb, closeappweb, searchWeather, tellTime, searchGoogle, searchYoutube, volumedown, volumeup

class JarvisAssistant:
    def __init__(self, access_key, keyword="jarvis"):
        self.access_key = access_key
        self.keyword = keyword
        self.running = False
        self.thread = None
        self.porcupine = None

    async def speak_async(self, audio):
        """Convert text to speech using edge-tts with the 'en-GB-RyanNeural' voice."""
        voice = 'en-GB-RyanNeural'
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
            print("Listening...")
            try:
                audio = r.listen(source, timeout=timeout, phrase_time_limit=phrase_time_limit)
            except sr.WaitTimeoutError:
                return "None"

        try:
            print("Understanding...")
            query = r.recognize_google(audio, language='en-us')
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
            frames_per_buffer=512
        )

        self.porcupine = pvporcupine.create(access_key=self.access_key, keywords=[self.keyword])

        print("Listening for the wake word...")
        while self.running:
            pcm = stream.read(self.porcupine.frame_length, exception_on_overflow=False)
            pcm = [int.from_bytes(pcm[i:i+2], byteorder='little', signed=True) for i in range(0, len(pcm), 2)]
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
            query = self.takeCommand(timeout=None, phrase_time_limit=None)
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

