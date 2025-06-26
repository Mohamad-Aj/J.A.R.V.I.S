import psycopg2
import requests
import json
from bs4 import BeautifulSoup
import openai
from dotenv import load_dotenv
import os, json, jwt

load_dotenv()

JWT_SECRET = os.getenv("JWT_SECRET")
class NewsFetcher:
    def __init__(self, db_url):
        self.db_url = db_url
        self.conn = None
        self.cursor = None

    def connect_to_db(self):
        print("Attempting to connect to the database...")
        try:
            self.conn = psycopg2.connect(self.db_url)
            self.cursor = self.conn.cursor()
            print("Database connection established.")
        except Exception as e:
            print(f"Error connecting to database: {e}")

    def close_db_connection(self):
        print("Closing database connection...")
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
        print("Database connection closed.")

    def fetch_user_preferences(self, user_id):
        """
        Fetch user hobbies and interests from the database.
        """
        print(f"Fetching preferences for user_id: {user_id}")
        try:
            # Fetch hobbies
            self.cursor.execute(
                "SELECT hobby FROM hobbies WHERE user_id = %s", (user_id,)
            )
            hobbies = [row[0] for row in self.cursor.fetchall()]
            print(f"Fetched hobbies: {hobbies}")

            # Fetch interests
            self.cursor.execute(
                "SELECT interest FROM interests WHERE user_id = %s", (user_id,)
            )
            interests = [row[0] for row in self.cursor.fetchall()]
            print(f"Fetched interests: {interests}")

            return hobbies + interests
        except Exception as e:
            print(f"Error fetching user preferences: {e}")
            return []


class YnetScraper:
    def __init__(self, base_url="https://www.ynetnews.com"):
        self.base_url = base_url
        self.categories = {
            "news": "/category/3082",  # Israel News
            "sports": "/culture/category/4386",  # Sports
            "technology": "/business/category/10006",  # Technology
            "business": "/business",  # Business
            "health": "/health_science",  # Health
            "entertainment": "/culture",  # Entertainment
            "travel": "/travel",  # Travel
            "food": "/culture/category/13193",
        }

    def fetch_articles(self):
        """
        Scrape articles from multiple Ynet categories.
        """
        articles = []
        for category_name, category_path in self.categories.items():
            url = f"{self.base_url}{category_path}"
            print(f"Fetching articles from {category_name} category: {url}")
            response = requests.get(url)
            if response.status_code != 200:
                print(
                    f"Failed to fetch articles from {category_name} category: {response.status_code}"
                )
                continue

            soup = BeautifulSoup(response.content, "html.parser")

            for item in soup.find_all("div", class_="slotTitle"):
                title = item.get_text(strip=True)
                link = item.find("a")["href"]
                full_link = (
                    f"{self.base_url}{link}" if not link.startswith("http") else link
                )
                # Look for the slotSubTitle (description) sibling
                description_item = item.find_next_sibling("div", class_="slotSubTitle")
                description = (
                    description_item.get_text(strip=True)
                    if description_item
                    else "No description available"
                )

                articles.append(
                    {
                        "title": title,
                        "link": full_link,
                        "description": description,
                        "category": category_name,
                    }
                )

        print(f"Fetched a total of {len(articles)} articles from all categories.")
        return articles

    def filter_articles_by_preferences(self, articles, preferences):
        """
        Filter articles based on user preferences (hobbies/interests), considering both
        title and description. Uses OpenAI API to validate description relevance.
        """
        filtered_articles = []
        print(f"Filtering articles by preferences: {preferences}")

        for article in articles:
            # Check if the title matches any preferences
            title_matches = any(
                preference.lower() in article["title"].lower()
                for preference in preferences
            )

            # If title matches, use OpenAI API to validate description relevance
            if title_matches:

                print(f"Validating description for: {article['title']}")
                try:
                    prompt = (
                        f"Check if the following description and title are related to these preferences or any of their sub perfrences like sports:basketball,football etc. the prefrences are: {preferences}\n\n"
                        f"Title:{article['title']} Description: {article['description']}\n\n"
                        f"Respond 'Yes' if related or 'No' if unrelated."
                    )
                    response = openai.chat.completions.create(
                        model="4o",
                        messages=[{"role": "user", "content": prompt}],
                        max_tokens=5,
                        temperature=0.4,
                    )
                    is_relevant = (
                        True
                        if "yes" in response.choices[0].message.content.strip().lower()
                        else False
                    )

                    if is_relevant:
                        filtered_articles.append(article)
                except Exception as e:
                    print(f"Error using OpenAI API: {e}")
                    # If the API fails, fallback to including the article
                    filtered_articles.append(article)

        print(f"Found {len(filtered_articles)} relevant articles.")
        return filtered_articles


def get_user_id_from_config(file_path: str) -> str | None:
    """
    Return the user_id regardless of whether the config stores a raw ID
    or a JWT token.

    Works both in dev mode and in a PyInstaller-frozen EXE.
    """
    try:
        # in a frozen app resolve the file inside …\\_internal
        from UUtils import resource_path12          # safe even in dev mode
        file_path = resource_path12(file_path)

        with open(file_path, "r", encoding="utf-8") as f:
            cfg = json.load(f)

        # new format ➜ JWT token
        if "token" in cfg and JWT_SECRET:
            payload = jwt.decode(cfg["token"], JWT_SECRET, algorithms=["HS256"])
            return payload.get("user_id")

        # old format ➜ raw id
        return cfg.get("user_id")
    except Exception as e:
        print(f"[get_user_id_from_config] error: {e}")
        return None


# requestnews.py
from PyQt6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QLabel, QTextBrowser
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon


class NewsWindow(QMainWindow):
    def __init__(self, preferences):
        super().__init__()
        self.setWindowTitle("Jarvis - Latest News")
        self.setFixedSize(620, 480)
        self.setWindowIcon(QIcon("icon.png"))

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        layout = QVBoxLayout(self.central_widget)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)
        self.central_widget.setStyleSheet("background-color: #333333;")

        self.text_browser = QTextBrowser()
        self.text_browser.setOpenExternalLinks(True)

        self.text_browser.setStyleSheet(
            """
            QTextBrowser {
                background-color: #2e2e2e;
                color: #eaeaea;
                font-size: 14px;
                font-family: 'Courier New', monospace;
                border: 1px solid #666666;
                border-radius: 8px;
                padding: 10px;
            }
        """
        )
        layout.addWidget(self.text_browser)

        self.load_news(preferences)

    def load_news(self, preferences):
        scraper = YnetScraper()
        all_articles = scraper.fetch_articles()
        relevant_articles = scraper.filter_articles_by_preferences(
            all_articles, preferences
        )

        if relevant_articles:
            for article in relevant_articles:
                self.text_browser.append(f"<b>{article['title']}</b>")
                self.text_browser.append(f"{article['description']}")
                self.text_browser.append(
                    f"<a href='{article['link']}' style='color: #1e90ff;'>Read more</a>"
                )
                self.text_browser.append("-" * 40)
        else:
            self.text_browser.append("No relevant news found.")


# # Example Usage
# if __name__ == "__main__":
#     DATABASE_URL = "postgresql://postgres:Jarvisgroup15@db.nsgeslmkrejtlifazhnu.supabase.co:5432/postgres?sslmode=require"
#     CONFIG_FILE_PATH = "user_config.json"

#     # Step 1: Load user_id from config file
#     user_id = get_user_id_from_config(CONFIG_FILE_PATH)
#     if not user_id:
#         print("User ID not found in the configuration file.")
#     else:
#         # Step 2: Fetch user preferences from the database
#         news_fetcher = NewsFetcher(DATABASE_URL)
#         news_fetcher.connect_to_db()
#         user_preferences = news_fetcher.fetch_user_preferences(user_id)
#         news_fetcher.close_db_connection()

#         # Step 3: Scrape Ynet and filter articles based on preferences
#         if user_preferences:
#             scraper = YnetScraper()
#             all_articles = scraper.fetch_articles()
#             relevant_articles = scraper.filter_articles_by_preferences(
#                 all_articles, user_preferences
#             )

#             # Step 4: Display filtered articles
#             if relevant_articles:
#                 print("Relevant Articles:")
#                 for article in relevant_articles:
#                     print(f"Title: {article['title']}")
#                     print(f"Link: {article['link']}")
#                     print(f"Description: {article['description']}")
#                     print("-" * 40)
#             else:
#                 print("No relevant articles found.")
#         else:
#             print("No user preferences found.")
