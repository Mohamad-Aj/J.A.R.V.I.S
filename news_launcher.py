# news_launcher.py

import sys
from PyQt6.QtWidgets import QApplication
from RequestNews import NewsWindow, NewsFetcher, get_user_id_from_config


def main():
    DATABASE_URL = "postgresql://postgres:Jarvisgroup15@db.nsgeslmkrejtlifazhnu.supabase.co:5432/postgres?sslmode=require"
    DATABASE_URL = "postgresql://postgres.nsgeslmkrejtlifazhnu:Jarvisgroup15@aws-0-eu-central-1.pooler.supabase.com:6543/postgres"

    CONFIG_FILE_PATH = "user_config.json"

    user_id = get_user_id_from_config(CONFIG_FILE_PATH)
    if not user_id:
        print("User ID not found.")
        return

    fetcher = NewsFetcher(DATABASE_URL)
    fetcher.connect_to_db()
    preferences = fetcher.fetch_user_preferences(user_id)
    fetcher.close_db_connection()

    app = QApplication(sys.argv)
    window = NewsWindow(preferences)
    window.show()
    sys.exit(app.exec())
