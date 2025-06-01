import json
import psycopg2
from urllib.parse import urlparse
from playwright.sync_api import sync_playwright

# your Supabase Postgres URL
DATABASE_URL = "postgresql://postgres:Jarvisgroup15@db.nsgeslmkrejtlifazhnu.supabase.co:5432/postgres"
DATABASE_URL = "postgresql://postgres.nsgeslmkrejtlifazhnu:Jarvisgroup15@aws-0-eu-central-1.pooler.supabase.com:6543/postgres"


class FormFillerAgent:
    def __init__(self, config_path: str, user_config_path: str, headless: bool = True):
        # 1) Load form-selectors/config
        with open(config_path, "r", encoding="utf-8") as f:
            self.forms_config = json.load(f)

        # 2) Load user_id from user_config.json
        # 2) Load & decode JWT from user_config.json
        import jwt, os
        from dotenv import load_dotenv

        load_dotenv()
        JWT_SECRET = os.getenv("JWT_SECRET")
        if not JWT_SECRET:
            raise ValueError("JWT_SECRET not set in .env")

        with open(user_config_path, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        token = cfg.get("token")
        if not token:
            raise ValueError("user_config.json must contain a 'token' field")

        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        except jwt.PyJWTError as e:
            raise ValueError(f"Invalid token in user_config.json: {e}")

        user_id = payload.get("user_id")
        if not user_id:
            raise ValueError("Decoded JWT payload is missing 'user_id'")

        # 3) Pull user_data from the database
        self.user_data = self._load_user_data_from_db(user_id)

        # 4) Headless flag for playwright
        self.headless = headless

    def _load_user_data_from_db(self, user_id: str) -> dict:
        """Fetch profile, hobbies, interests, and responses, assemble into dict."""
        conn = psycopg2.connect(DATABASE_URL)
        try:
            cur = conn.cursor()

            # a) Profile
            cur.execute(
                """
                SELECT first_name, last_name, email, phone,
                       street_name, house_apartment, city, state, zip_code, country,
                       to_char(date_of_birth, 'YYYY-MM-DD')
                  FROM users
                 WHERE id = %s
                """,
                (user_id,),
            )
            row = cur.fetchone()
            if not row:
                raise ValueError(f"No user found with id {user_id}")

            (
                first_name,
                last_name,
                email,
                phone,
                street,
                house,
                city,
                state,
                zip_code,
                country,
                dob,
            ) = row

            # build the base dict
            data = {
                # original DB fields
                "First Name": first_name,
                "Last Name": last_name,
                "Email": email,
                "Phone": phone,
                "Street Name": street,
                "House/Apartment": house,
                "City": city,
                "State": state,
                "Zip Code": zip_code,
                "Country": country,
                "Date of Birth": dob,
            }

            # ───────────────────────────────────────────────────────────
            # **NEW** name fields injection:
            full = f"{first_name} {last_name}".strip()
            data["name"] = full
            data["full name"] = full
            data["firstname"] = first_name
            data["lastname"] = last_name
            # ───────────────────────────────────────────────────────────

            # b) Hobbies
            cur.execute("SELECT hobby FROM hobbies WHERE user_id = %s", (user_id,))
            data["Hobbies"] = [r[0] for r in cur.fetchall()]

            # c) Interests
            cur.execute("SELECT interest FROM interests WHERE user_id = %s", (user_id,))
            data["Interests"] = [r[0] for r in cur.fetchall()]

            # d) Hobby responses
            cur.execute(
                """
                SELECT hobby, tag, answer
                  FROM hobby_responses
                 WHERE user_id = %s
                """,
                (user_id,),
            )
            hobby_resps = [
                {"Hobby": h, "Tag": t, "Answer": a} for (h, t, a) in cur.fetchall()
            ]
            data["Responses for Hobbies"] = hobby_resps

            # e) Interest responses
            cur.execute(
                """
                SELECT interest, tag, answer
                  FROM interest_responses
                 WHERE user_id = %s
                """,
                (user_id,),
            )
            int_resps = [
                {"Interest": i, "Tag": t, "Answer": a} for (i, t, a) in cur.fetchall()
            ]
            data["Responses for Interests"] = int_resps

            return data

        finally:
            cur.close()
            conn.close()

    def _guess_value(self, field_name: str) -> str:
        key = field_name.lower()
        data = self.user_data
        if key in ("birthday_month", "birthday_day", "birthday_year"):
            y, m, d = data.get("Date of Birth", "").split("-")  # "YYYY-MM-DD"
            return {
                "birthday_month": str(int(m)),  # "10" -> "10",  "03" -> "3"
                "birthday_day": str(int(d)),  # "01" -> "1"
                "birthday_year": y,  # already "2002"
            }[key]

        # exact key match
        if field_name in data:
            return data[field_name]
        for k, v in data.items():
            if k.lower() == key:
                return v

        # fallback heuristics
        if "full" in key:
            return data.get("name", "")
        if "first" in key or "last" in key:
            parts = data.get("name", "").split(" ", 1)
            return parts[0] if "first" in key else (parts[1] if len(parts) > 1 else "")
        if "email" in key:
            return data.get("Email", "")
        if "pass" in key:
            return data.get("password", "")
        if "phone" in key or "mobile" in key:
            return data.get("Phone", "")
        if "user" in key:
            return data.get("username", data.get("name", ""))
        return ""

    def fill_form(
        self, site_key: str, status_callback=None, start_url: str = None
    ) -> None:
        cfg = self.forms_config.get(site_key)
        if not cfg:
            raise ValueError(f"No form config for site: {site_key}")
        status_callback and status_callback(f"Launching browser for {site_key}...")

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=self.headless)
            page = browser.new_page()

            # 1) Navigate
            url_to_go = start_url or cfg["url"]
            status_callback and status_callback(f"→ Navigating to {url_to_go}")
            page.goto(url_to_go, wait_until="networkidle")

            pre = cfg.get("pre_click")
            if pre:
                status_callback and status_callback(f"→ Clicking pre‐step: {pre}")
                page.click(pre)
                # wait for your first real field to appear
                first_field = list(cfg["fields"].values())[0]
                page.wait_for_selector(first_field, timeout=10_000)

            # 2) CAPTCHA
            if cfg.get("captcha_selector"):
                try:
                    if page.is_visible(cfg["captcha_selector"], timeout=5_000):
                        status_callback and status_callback(
                            "🛑 CAPTCHA—please solve it…"
                        )
                        input()
                except:
                    pass

            # 3) Amazon two-step
            if site_key == "amazon":
                if page.is_visible("input#ap_email", timeout=5_000):
                    status_callback and status_callback("→ Amazon email step…")
                    page.fill("input#ap_email", self.user_data["Email"])
                    page.click("input#continue")
                    page.wait_for_selector("input[name='customerName']", timeout=10_000)

            # 4) Facebook special
            if site_key == "facebook":
                for fld in ("firstname", "lastname"):
                    sel = cfg["fields"][fld]
                    page.wait_for_selector(sel)
                    page.fill(sel, self.user_data[fld])
                e1 = cfg["fields"]["email"]
                page.fill(e1, self.user_data["Email"])
                page.locator(e1).press("Tab")
                e2 = cfg["fields"]["email_confirmation"]
                page.wait_for_selector(e2, timeout=10_000)
                page.fill(e2, self.user_data["Email"])
                page.fill(cfg["fields"]["password"], self.user_data.get("password", ""))
                for part in ("birthday_month", "birthday_day", "birthday_year"):
                    val = self.user_data.get(part, "")
                    if val:
                        page.select_option(cfg["fields"][part], val)
                gender_map = {"female": "1", "male": "2", "custom": "-1"}
                g = self.user_data.get("gender", "").lower()
                if g in gender_map:
                    page.check(f"input[name='sex'][value='{gender_map[g]}']")

            # 5) LinkedIn two-step
            elif site_key == "linkedin":
                for fld in ("email-address", "password"):
                    sel = cfg["fields"][fld]
                    page.wait_for_selector(sel)
                    page.fill(sel, self._guess_value(fld))
                page.click(cfg["submit_button"])
                page.wait_for_load_state("networkidle")

                for fld in ("first-name", "last-name"):
                    sel = cfg["fields"][fld]
                    page.wait_for_selector(sel)
                    page.fill(sel, self._guess_value(fld))
                page.click(cfg["submit_button"])
                page.wait_for_load_state("networkidle")

            if site_key == "x":
                # 1) Navigate + pre‐click “Create account”
                # page.goto(url_to_go, wait_until="domcontentloaded")
                # if pre := cfg.get("pre_click"):
                #     status_callback and status_callback(f"→ Clicking pre‐step: {pre}")
                #     page.click(pre)

                # 2) Wait for the name field (and the selects) to appear
                page.wait_for_selector(cfg["fields"]["name"], timeout=10_000)

                # 3) Fill **all** fields in order:
                #    name, emailOrPhone, birthday_month, birthday_day, birthday_year
                for field, selector in cfg["fields"].items():
                    val = self._guess_value(field)
                    status_callback and status_callback(f"Filling {field}: {val}")
                    page.wait_for_selector(selector, timeout=5_000)

                    # if it's a <select>, pick the option; otherwise fill text
                    try:
                        page.select_option(selector, val)
                    except:
                        page.fill(selector, val)

                # 2) Month ▸ Day ▸ Year — re‑locate selects each time
                # month
                page.select_option(
                    "select#SELECTOR_1", self._guess_value("birthday_month")
                )

                # day  (first select whose first non‑blank option is "1")
                page.select_option(
                    "select#SELECTOR_2", self._guess_value("birthday_day")
                )

                # year (select whose first non‑blank option is a 4‑digit year)
                page.select_option(
                    "select#SELECTOR_3", self._guess_value("birthday_year")
                )

                # 4) Click the single “Next” button to complete signup
                status_callback and status_callback(
                    "→ Clicking Next to submit X signup"
                )
                next_sel = cfg["submit_button"]
                page.wait_for_selector(next_sel, timeout=10_000)
                page.click(next_sel)

                # 5) Done
                status_callback and status_callback(
                    "✅ X signup flow filled—verify and close."
                )
                print("Press ENTER to close browser.")
                input()
                return

            # 6) Everyone else: generic fill
            else:
                for field, selector in cfg["fields"].items():
                    val = self._guess_value(field)
                    status_callback and status_callback(f"Filling {field}…")
                    if selector.startswith("select"):
                        # for a date field, val should be "MM" or "DD" or "YYYY"
                        page.select_option(selector, val)
                    else:
                        page.wait_for_selector(selector, timeout=10_000)

                        page.fill(selector, val)

            # 7) Post-submit clicks
            for sel in cfg.get("post_submit", []):
                page.wait_for_selector(sel, timeout=10_000)
                page.click(sel)

            page.wait_for_load_state("networkidle")

            # 8) Leave it open
            status_callback and status_callback("✅ Done—browser will stay open.")
            print("Form filled. Press ENTER here to finish and close.")
            input()

        status_callback and status_callback(f"Finished filling for {site_key}!")
