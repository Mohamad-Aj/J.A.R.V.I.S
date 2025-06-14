import datetime
import os
import pickle
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from UUtils import resource_path12

SCOPES = ["https://www.googleapis.com/auth/calendar.events"]


def authenticate_google(user_email: str):
    creds = None
    token_file = f"token_{user_email}.pickle"  # unique per user

    if os.path.exists(token_file):
        with open(token_file, "rb") as token:
            creds = pickle.load(token)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(resource_path12("credentials.json"), SCOPES)
            creds = flow.run_local_server(port=0)

        with open(token_file, "wb") as token:
            pickle.dump(creds, token)

    return build("calendar", "v3", credentials=creds)


def add_event_to_calendar(
    user_email: str, title: str, description: str, start_datetime: datetime.datetime
):
    service = authenticate_google(user_email)
    event = {
        "summary": title,
        "description": description,
        "start": {
            "dateTime": start_datetime.isoformat(),
            "timeZone": "Asia/Jerusalem",
        },
        "end": {
            "dateTime": (start_datetime + datetime.timedelta(hours=1)).isoformat(),
            "timeZone": "Asia/Jerusalem",
        },
    }
    service.events().insert(calendarId="primary", body=event).execute()
