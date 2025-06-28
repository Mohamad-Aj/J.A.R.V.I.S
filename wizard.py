import customtkinter as ctk
from tkinter import messagebox
import json
from tkinter import ttk  # For improved scrolling
import datetime
from openai import OpenAI
import openai
from dotenv import load_dotenv
import os
from tkinter import Text
from db_insertion import insert_user_data
import jwt
from UUtils import bundle_root, copy_to_internal


LOCAL_STORAGE_FILE = bundle_root() / "user_config.json"

load_dotenv()


class RegistrationWizard(ctk.CTk):
    def __init__(self, on_registration_complete=None):
        super().__init__()

        self.jwt_secret = os.getenv("JWT_SECRET")
        if not self.jwt_secret:
            raise ValueError("JWT_SECRET not found. Please set it in your .env file.")
        # Window setup
        self.title("Jarvis Registration Wizard")
        self.geometry("800x600")  # Slightly smaller fixed size window
        self.configure(fg_color="#f0f0f0")  # Light background
        self.on_registration_complete = on_registration_complete
        self.selected_preferences = []
        self.current_question_index = 0
        self.flag = 0

        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        if not self.openai_api_key:
            raise ValueError(
                "OpenAI API key not found. Please set it in your .env file."
            )

        self.conversation = [
            {
                "role": "system",
                "content": (
                    "You are a friendly and helpful assistant. You must ask only one specific and clear question at a time. "
                    "Avoid combining multiple topics or questions in a single response. Keep questions short and focused."
                ),
            }
        ]

        # Initialize user input variables
        self.user_data = {
            "First Name": ctk.StringVar(),
            "Last Name": ctk.StringVar(),
            "Email": ctk.StringVar(),
            "Phone": ctk.StringVar(),
            "Street Name": ctk.StringVar(),
            "House/Apartment": ctk.StringVar(),
            "City": ctk.StringVar(),
            "State": ctk.StringVar(),
            "Zip Code": ctk.StringVar(),
            "Country": ctk.StringVar(),
            "Date of Birth": ctk.StringVar(),
            # "Gender": ctk.StringVar(),
            "Hobbies": [],
            "Interests": [],
            "Preferred Topics": [],
        }

        # Predefined options for cards
        self.hobbies_options = ["Sports", "Art", "Music", "Reading", "Gaming"]
        self.preferences_options = [
            "Technology",
            "Health",
            "Travel",
            "Education",
            "Food",
        ]

        # Create a sidebar for the steps
        self.sidebar = ctk.CTkFrame(
            self, fg_color="#2d3142", width=150, corner_radius=10
        )
        self.sidebar.pack(side="left", fill="y", padx=(5, 0), pady=5)

        # Step titles
        self.steps_titles = [
            "Personal Info",
            "Preferences",
            "Setup Options",
            "Agreement",
        ]
        self.current_step = None

        # Create step indicators in the sidebar
        self.step_labels = []
        for i, title in enumerate(self.steps_titles):
            step_label = ctk.CTkLabel(
                self.sidebar,
                text=f"{i + 1}. {title}",
                font=ctk.CTkFont(size=14, weight="bold"),
                text_color="#f0f0f0" if i == 0 else "#9c9c9c",
                anchor="w",
            )
            step_label.pack(fill="x", pady=10, padx=10)
            self.step_labels.append(step_label)

        # Create frames for the steps
        self.steps = [
            self.create_step1(),
            self.create_step2(),
            self.create_step3(),
            self.create_step4(),
        ]

        # Show the first step
        self.show_step(0)

    def create_step1(self):
        """Step 1: Personal Information."""
        frame = self.create_step_frame()

        # Title
        ctk.CTkLabel(
            frame,
            text="Personal Information",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="#2d3142",
        ).pack(pady=10)

        # Single column layout for inputs
        input_grid = ctk.CTkFrame(frame, fg_color="transparent")
        input_grid.pack(fill="both", expand=True, padx=20, pady=10)

        # Inputs in a single column
        inputs = [
            ("First Name", "entry", "Enter your first name"),
            ("Last Name", "entry", "Enter your last name"),
            ("Email", "entry", "Enter your email address"),
            ("Phone", "entry", "Enter your phone number"),
            ("Date of Birth", "custom_date", None),
            ("Street Name", "entry", "Enter your street name"),
            ("State", "entry", "Enter your state"),
            ("House/Apartment", "entry", "Enter house/apartment details"),
            ("City", "entry", "Enter your city"),
            ("Zip Code", "entry", "Enter your zip code"),
            ("Country", "entry", "Enter your country"),
        ]

        for i, (label, widget, placeholder) in enumerate(inputs):
            self.create_input(
                input_grid,
                label,
                row=i,
                column=0,
                widget=widget,
                placeholder=placeholder,
            )

        # Navigation buttons in a separate container
        nav_frame = ctk.CTkFrame(frame, fg_color="transparent")
        nav_frame.pack(fill="x", pady=10)
        next_button = ctk.CTkButton(
            nav_frame,
            text="Next",
            command=lambda: self.show_step(1),
            fg_color="#2d3142",
        )
        next_button.pack(side="top", padx=(5, 0))
        return frame

    def create_step2(self):
        """Step 2: Preferences."""
        frame = self.create_step_frame()

        # Title
        ctk.CTkLabel(
            frame,
            text="Preferences",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="#2d3142",
        ).pack(pady=10)

        # Scrollable frame
        scrollable_frame = ctk.CTkFrame(frame, fg_color="transparent")
        scrollable_frame.pack(fill="both", expand=True, pady=5, padx=5)

        canvas = ctk.CTkCanvas(
            scrollable_frame, bg="white", highlightthickness=0, height=800
        )
        scrollbar = ttk.Scrollbar(
            scrollable_frame, orient="vertical", command=canvas.yview
        )
        inner_frame = ctk.CTkFrame(canvas, fg_color="transparent")

        canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)
        canvas.create_window((0, 0), window=inner_frame, anchor="nw")

        inner_frame.bind(
            "<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        # Hobbies section
        self.create_card_selection(
            inner_frame, "Hobbies", self.hobbies_options, self.user_data["Hobbies"]
        )

        # Interests section
        self.create_card_selection(
            inner_frame,
            "Interests",
            self.preferences_options,
            self.user_data["Interests"],
        )

        # Navigation buttons in a separate container
        nav_frame = ctk.CTkFrame(frame, fg_color="transparent")
        nav_frame.pack(fill="x", pady=5)
        self.add_navigation_buttons(
            nav_frame,
            back_command=lambda: self.show_step(0),
            next_command=lambda: self.show_step(2),
        )

        return frame

    def create_step3(self):
        """Step 3: Interactive Chatbot Stage with OpenAI."""
        frame = self.create_step_frame()

        # Title
        ctk.CTkLabel(
            frame,
            text="Interactive Chat Setup",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="#2d3142",
        ).pack(pady=10)

        # Chat area
        chat_frame = ctk.CTkFrame(frame, fg_color="transparent")
        chat_frame.pack(fill="both", expand=True, padx=20, pady=10)

        # Chat history display
        self.chat_history = ctk.CTkTextbox(
            chat_frame, width=400, height=300, wrap="word", state="disabled"
        )
        self.chat_history.pack(fill="both", expand=True, pady=10)

        # Input field for user message
        input_frame = ctk.CTkFrame(chat_frame, fg_color="transparent")
        input_frame.pack(fill="x", pady=5)

        self.user_input = ctk.StringVar()
        ctk.CTkEntry(input_frame, textvariable=self.user_input, width=300).pack(
            side="left", padx=5
        )

        send_button = ctk.CTkButton(
            input_frame,
            text="Send",
            command=self.process_user_response,
            fg_color="#2d3142",
        )
        send_button.pack(side="right", padx=5)

        # Navigation button
        nav_frame = ctk.CTkFrame(frame, fg_color="transparent")
        nav_frame.pack(fill="x", pady=10)
        self.add_navigation_buttons(
            nav_frame,
            back_command=lambda: self.show_step(1),
            next_command=lambda: self.show_step(3),
        )

        # Collect latest preferences and reset conversation state
        self.collect_visible_cards()
        self.initialize_chatbot_state()

        # self.start_chatbot()

        return frame

    def create_step4(self):
        """Step 4: Agreements to Terms and Conditions."""
        frame = self.create_step_frame()

        # Title
        ctk.CTkLabel(
            frame,
            text="Terms and Conditions",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="#2d3142",
        ).pack(pady=10)

        # Scrollable terms and conditions text
        terms_frame = ctk.CTkFrame(frame, fg_color="transparent")
        terms_frame.pack(fill="both", expand=True, padx=20, pady=10)

        canvas = ctk.CTkCanvas(terms_frame, bg="white", highlightthickness=0)
        scrollbar = ttk.Scrollbar(terms_frame, orient="vertical", command=canvas.yview)
        content_frame = ctk.CTkFrame(canvas, fg_color="white")

        canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)
        canvas.create_window((0, 0), window=content_frame, anchor="nw")

        content_frame.bind(
            "<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        # Add agreement text
        agreement_text = (
            "By proceeding, you agree to the following terms and conditions:\n\n"
            "1. Data Collection: This application may access and collect data on your computer, "
            "including personal files, system logs, browsing history, and user activity.\n\n"
            "2. Activity Monitoring: When enabled, the application may monitor your activity for "
            "purposes of providing personalized assistance or improving functionality. This includes "
            "tracking active applications, analyzing usage patterns, and collecting contextual data.\n\n"
            "3. Microphone Access: The application may use your microphone to process voice commands "
            "and interactions. Audio data will only be processed in real-time and will not be stored unless explicitly stated.\n\n"
            "4. Data Storage: Collected data may be stored locally or in secure cloud storage for analysis "
            "and to enhance your experience. Data retention policies will comply with industry standards.\n\n"
            "5. Privacy Assurance: We take your privacy seriously. Collected data will be used only for purposes "
            "stated within this agreement and will not be shared with third parties without your consent.\n\n"
            "6. System Access: By using this application, you agree to allow it to access system resources "
            "necessary for its operation, including network access, file management, microphone, and process execution.\n\n"
            "7. Internet Access: The application may require internet access to communicate with APIs, download updates, "
            "or provide cloud-based services. Your data transmission will be secured.\n\n"
            "8. Updates and Changes: This application may update its features and terms from time to time. "
            "By continuing to use the application after an update, you agree to the new terms.\n\n"
            "9. Termination: If you disagree with any of these terms, you must discontinue using the application immediately. "
            "You may also contact support to request the deletion of any data collected.\n\n"
        )

        ctk.CTkLabel(
            content_frame,
            text=agreement_text,
            font=ctk.CTkFont(size=12),
            text_color="#2d3142",
            wraplength=400,
            justify="left",
            anchor="nw",
        ).pack(pady=10, padx=10)

        # Checkbox for agreement
        self.agreed_to_terms = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            frame,
            text_color="black",
            text="I agree to the terms and conditions",
            variable=self.agreed_to_terms,
            font=ctk.CTkFont(size=12),
        ).pack(pady=10)

        # Navigation buttons
        nav_frame = ctk.CTkFrame(frame, fg_color="transparent")
        nav_frame.pack(fill="x", pady=5)
        self.add_navigation_buttons(
            nav_frame,
            back_command=lambda: self.show_step(2),
            finish_command=self.finish_registration,
        )

        return frame

    def initialize_chatbot_state(self):
        """Initialize or reset chatbot state."""
        # Reset question tracking and current index
        self.questions_per_topic = {pref: 0 for pref in self.selected_preferences}
        self.current_question_index = 0
        self.conversation = [
            {
                "role": "system",
                "content": (
                    "You are a friendly and helpful assistant. You must ask only one specific and clear question at a time. "
                    "Avoid combining multiple topics or questions in a single response. Keep questions short and focused."
                ),
            }
        ]

    def start_chatbot(self):
        """Start chatbot interaction dynamically with updated preferences."""
        # Collect visible cards to ensure the latest preferences are used
        self.collect_visible_cards()

        if not self.selected_preferences:
            self.update_chat_history(
                "Jarvis",
                "No preferences were found from the previous step. Please go back to Step 2 and select preferences.",
            )
            return

        # Separate hobbies and interests
        self.hobby_topics = self.user_data["Hobbies"]
        self.interest_topics = self.user_data["Interests"]
        self.current_hobby_index = 0
        self.current_interest_index = 0

        # Initialize chatbot state
        self.initialize_chatbot_state()

        # Start with hobbies
        self.flag = 2
        self.ask_next_question(is_hobby=True)

    def ask_next_question(self, is_hobby=True):
        """
        Ask specific, relevant, and context-aware follow-up questions
        for hobbies and interests.
        """
        topics = self.hobby_topics if is_hobby else self.interest_topics
        current_index = (
            self.current_hobby_index if is_hobby else self.current_interest_index
        )

        if current_index < len(topics):
            current_topic = topics[current_index]

            # Check if we've already asked 3 questions for this topic
            if self.questions_per_topic.get(current_topic, 0) < 3:
                try:
                    # Determine the type of question to ask
                    question_type = "hobby" if is_hobby else "interest"
                    prompt = f"""
                    You are a friendly assistant gathering details about the user's {question_type} '{current_topic}'.
                    Generate a specific follow-up question that is relevant to a {question_type}.
                    Example:
                    - For hobbies: "What do you enjoy most about this hobby?" or "How often do you engage in this activity?"
                    - For interests: "What topics within this interest are your favorite?" or "Have you explored related fields?"

                    Avoid generic or philosophical questions.
                    """

                    response = openai.chat.completions.create(
                        model="gpt-3.5-turbo",
                        messages=self.conversation
                        + [{"role": "user", "content": prompt}],
                        max_tokens=50,  # Limit response length
                        temperature=0.5,  # Moderate randomness
                    )
                    question = response.choices[0].message.content.strip()

                    # Append the generated question to the conversation
                    self.conversation.append({"role": "assistant", "content": question})

                    # Display the question in the chat
                    self.update_chat_history("Jarvis", question)

                    # Increment the question count for this topic
                    self.questions_per_topic[current_topic] = (
                        self.questions_per_topic.get(current_topic, 0) + 1
                    )
                except Exception as e:
                    self.update_chat_history(
                        "Jarvis",
                        f"An error occurred while generating the question: {str(e)}",
                    )
            else:
                # Move to the next topic if this one is done
                if is_hobby:
                    self.current_hobby_index += 1
                    if self.current_hobby_index >= len(self.hobby_topics):
                        # Switch to interests if hobbies are done
                        self.ask_next_question(is_hobby=False)
                    else:
                        self.ask_next_question(is_hobby=True)
                else:
                    self.current_interest_index += 1
                    self.ask_next_question(is_hobby=False)
        else:
            # If all topics are done
            self.flag = 1
            self.update_chat_history(
                "Jarvis",
                "Thank you for the information! The interaction is now complete.",
            )

    def process_user_response(self):
        """Process user's response to the chatbot."""
        response = self.user_input.get().strip()
        if not response:
            return

        # Update chat history with user's response
        self.update_chat_history("User", response)
        self.user_input.set("")  # Clear input field

        # Save the response to user data with tagging
        if self.current_hobby_index < len(self.hobby_topics):
            current_topic = self.hobby_topics[self.current_hobby_index]
            category = "Hobbies"
        elif self.current_interest_index < len(self.interest_topics):
            current_topic = self.interest_topics[self.current_interest_index]
            category = "Interests"
        else:
            return  # No more questions to process

        question = self.conversation[-1]["content"]  # Last question from the bot
        tag = self.generate_tag(question, response)  # Generate a tag for the response

        # Save response with tag
        if f"Responses for {category}" not in self.user_data:
            self.user_data[f"Responses for {category}"] = []
        self.user_data[f"Responses for {category}"].append(
            {"Tag": tag, "Answer": response}
        )

        # Ask the next question
        is_hobby = category == "Hobbies"
        self.ask_next_question(is_hobby=is_hobby)

    def update_chat_history(self, sender, message):
        """Update the chat history in the UI."""
        self.chat_history.configure(state="normal")

        # Determine background color based on sender
        if sender == "User":
            fg_color = "#ffffff"  # White background for user messages
            align = "right"

        else:
            fg_color = "#f0f0f0"  # Light gray background for bot messages
            align = "left"

        # Insert a spacer for visual separation
        self.chat_history.insert("end", "\n")

        # Insert the message with manual alignment
        if align == "right":
            # Pad the message to simulate right alignment
            padded_message = f"{message}\n"
        else:
            # Left-aligned message
            padded_message = f"{message}\n"

        # Apply formatting (background color simulation by line breaks)
        self.chat_history.insert("end", f"{sender}: {padded_message}")

        # Disable further editing
        self.chat_history.configure(state="disabled")
        self.chat_history.see("end")

    def collect_visible_cards(self):
        """Collect all visible cards in Step 2 as selected preferences."""
        # Reset the selected lists before collecting new data
        self.user_data["Hobbies"].clear()
        self.user_data["Interests"].clear()
        self.selected_preferences.clear()

        # Collect hobbies specifically from the hobbies section
        for row in self.hobbies_frame.winfo_children():  # Access hobbies cards
            for card in row.winfo_children():
                for widget in card.winfo_children():
                    if isinstance(
                        widget, ctk.CTkLabel
                    ):  # Look for labels containing card text
                        hobby = widget.cget("text")
                        if hobby not in self.user_data["Hobbies"]:
                            self.user_data["Hobbies"].append(hobby)

        # Collect interests specifically from the interests section
        for row in self.interests_frame.winfo_children():  # Access interests cards
            for card in row.winfo_children():
                for widget in card.winfo_children():
                    if isinstance(
                        widget, ctk.CTkLabel
                    ):  # Look for labels containing card text
                        interest = widget.cget("text")
                        if interest not in self.user_data["Interests"]:
                            self.user_data["Interests"].append(interest)

        # Combine hobbies and interests into selected_preferences
        self.selected_preferences = (
            self.user_data["Hobbies"] + self.user_data["Interests"]
        )

        # Reset chatbot state dynamically
        self.initialize_chatbot_state()

    def create_step_frame(self):
        """Helper method to create a step frame."""
        frame = ctk.CTkFrame(self, fg_color="#ffffff", corner_radius=10)
        return frame

    def create_input(
        self, parent, label, row, column, widget="entry", values=None, placeholder=None
    ):
        """Create an input field with a label in a grid layout."""
        input_frame = ctk.CTkFrame(parent, fg_color="transparent")
        input_frame.grid(row=row, column=column, padx=10, pady=5, sticky="w")

        ctk.CTkLabel(
            input_frame,
            text=label,
            font=ctk.CTkFont(size=12),
            text_color="#2d3142",
            width=150,
            anchor="w",
        ).pack(side="left", padx=5)

        if widget == "entry":
            entry = ctk.CTkEntry(
                input_frame,
                textvariable=self.user_data[label],
                width=200,
                fg_color="#2d3142",
            )
            if placeholder:
                entry.insert(0, placeholder)
                entry.configure(text_color="lightgray")
                entry.bind(
                    "<FocusIn>",
                    lambda e: (
                        entry.delete(0, "end") if entry.get() == placeholder else None
                    ),
                )
                entry.bind(
                    "<FocusOut>",
                    lambda e: (
                        entry.insert(0, placeholder) if entry.get() == "" else None
                    ),
                )
            entry.pack(side="left", padx=10)
        elif widget == "dropdown":
            ctk.CTkOptionMenu(
                input_frame,
                variable=self.user_data[label],
                values=values,
                corner_radius=12,
            ).pack(side="left", padx=10)
        elif widget == "custom_date":
            self.create_custom_datepicker(input_frame, label)

    def create_custom_datepicker(self, parent, label):
        """Create a custom date picker using scrollable dropdown menus."""
        current_year = datetime.date.today().year
        years = [str(year) for year in range(current_year - 100, current_year + 1)]
        months = [
            "Jan",
            "Feb",
            "Mar",
            "Apr",
            "May",
            "Jun",
            "Jul",
            "Aug",
            "Sep",
            "Oct",
            "Nov",
            "Dec",
        ]
        days = [str(day) for day in range(1, 32)]

        # Variables to store selected values
        day_var = ctk.StringVar(value="Day")
        month_var = ctk.StringVar(value="Month")
        year_var = ctk.StringVar(value="Year")

        # Create a common function for dropdowns
        def create_scrollable_menu(options, variable, width=10):
            dropdown_frame = ctk.CTkFrame(parent, fg_color="#ffffff", corner_radius=5)
            dropdown_frame.pack(side="left", padx=7)

            # Display the selected value
            display_button = ctk.CTkButton(
                dropdown_frame,
                textvariable=variable,
                # fg_color="#ffffff",
                text_color="#000000",
                fg_color="lightgray",
                width=width * 5.8,
                height=30,
                command=lambda: toggle_menu(),
            )
            display_button.pack()

            # Scrollable options menu
            menu_frame = ctk.CTkFrame(
                dropdown_frame, fg_color="#ffffff", corner_radius=5, width=width
            )
            canvas = ctk.CTkCanvas(
                menu_frame, height=250, bg="#ffffff", highlightthickness=0, width=width
            )
            scrollbar = ttk.Scrollbar(
                menu_frame, orient="vertical", command=canvas.yview
            )
            options_frame = ctk.CTkFrame(canvas, fg_color="#ffffff")

            canvas.create_window((0, 0), window=options_frame, anchor="nw")
            canvas.configure(yscrollcommand=scrollbar.set)

            # Populate menu with options
            for option in options:
                ctk.CTkButton(
                    options_frame,
                    text=option,
                    fg_color="#f0f0f0",
                    hover_color="#d0d0d0",
                    text_color="#000000",
                    width=width * 4,
                    height=25,
                    command=lambda opt=option: select_option(opt),
                ).pack(fill="x")

            options_frame.bind(
                "<Configure>",
                lambda e: canvas.configure(scrollregion=canvas.bbox("all")),
            )
            canvas.pack(side="left", fill="both", expand=True)
            scrollbar.pack(side="right", fill="y")
            menu_frame.pack_forget()  # Hide initially

            # Toggle menu visibility
            def toggle_menu():
                if menu_frame.winfo_ismapped():
                    menu_frame.pack_forget()
                else:
                    menu_frame.pack(side="top", fill="both", expand=False, pady=5)

            # Update selected value
            def select_option(opt):
                variable.set(opt)
                menu_frame.pack_forget()

        # Create scrollable menus for day, month, and year
        create_scrollable_menu(days, day_var)
        create_scrollable_menu(months, month_var)
        create_scrollable_menu(years, year_var)

        # Update the final date in the user data
        def update_date():
            selected_day = day_var.get()
            selected_month = (
                months.index(month_var.get()) + 1 if month_var.get() in months else 0
            )
            selected_year = year_var.get()
            if (
                selected_day != "Day"
                and selected_month != 0
                and selected_year != "Year"
            ):
                date_str = (
                    f"{selected_year}-{selected_month:02d}-{int(selected_day):02d}"
                )
                self.user_data[label].set(date_str)

        # Bind updates
        day_var.trace("w", lambda *args: update_date())
        month_var.trace("w", lambda *args: update_date())
        year_var.trace("w", lambda *args: update_date())

    def create_card_selection(self, parent, title, options, selected_list):
        """Create a card selection area for multiple choices."""
        section_frame = ctk.CTkFrame(parent, fg_color="transparent")
        section_frame.pack(pady=10, padx=10, fill="x")

        ctk.CTkLabel(
            section_frame,
            text=title,
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#2d3142",
        ).pack(anchor="w", pady=5)

        # Assign to the correct frame
        if title == "Hobbies":
            self.hobbies_frame = ctk.CTkFrame(section_frame, fg_color="transparent")
            self.hobbies_frame.pack(fill="x")
            parent_frame = self.hobbies_frame
            self.hobbies_entry = ctk.StringVar()  # Separate entry for Hobbies
        elif title == "Interests":
            self.interests_frame = ctk.CTkFrame(section_frame, fg_color="transparent")
            self.interests_frame.pack(fill="x")
            parent_frame = self.interests_frame
            self.interests_entry = ctk.StringVar()  # Separate entry for Interests

        # Create cards for the predefined options
        for i, option in enumerate(options):
            if i % 4 == 0:
                row_frame = ctk.CTkFrame(parent_frame, fg_color="transparent")
                row_frame.pack(fill="x", pady=5)
            self.create_card(row_frame, option, selected_list)

        # Add custom input option
        add_frame = ctk.CTkFrame(section_frame, fg_color="transparent")
        add_frame.pack(pady=5, fill="x")

        # Link the correct custom_entry to the Add button
        entry_var = self.hobbies_entry if title == "Hobbies" else self.interests_entry

        ctk.CTkEntry(
            add_frame, textvariable=entry_var, placeholder_text="Add your own..."
        ).pack(side="left", padx=5)
        ctk.CTkButton(
            add_frame,
            text="Add",
            command=lambda: self.add_custom_option(entry_var.get(), selected_list),
        ).pack(side="left", padx=5)

    def create_card(self, parent, option, selected_list):
        """Create an individual card with a delete button."""
        card_frame = ctk.CTkFrame(parent, fg_color="#e0e0e0", corner_radius=8)
        card_frame.pack(side="left", padx=5, pady=5, anchor="n")

        # Card text
        ctk.CTkLabel(
            card_frame, text=option, font=ctk.CTkFont(size=12), text_color="black"
        ).pack(side="left", padx=10)

        # Delete button
        delete_button = ctk.CTkButton(
            card_frame,
            text="x",
            width=20,
            height=20,
            fg_color="transparent",
            hover_color="lightgray",
            text_color="black",
            command=lambda: self.delete_card(card_frame, option, selected_list),
        )
        delete_button.pack(side="right", padx=5)

    def delete_card(self, card_frame, option, selected_list):
        """Delete the selected card and rearrange the remaining cards."""
        if option in selected_list:
            selected_list.remove(option)
        card_frame.destroy()

        # Rearrange the remaining cards
        self.rearrange_cards(selected_list)

    def rearrange_cards(self, selected_list):
        """Rearrange the cards dynamically after deletion."""
        # Determine the parent frame
        parent_frame = (
            self.hobbies_frame
            if selected_list == self.user_data["Hobbies"]
            else self.interests_frame
        )

        # Clear the existing rows
        for row in parent_frame.winfo_children():
            row.destroy()

        # Recreate cards based on the updated list
        for i, option in enumerate(selected_list):
            if i % 4 == 0:  # Start a new row every 4 cards
                row_frame = ctk.CTkFrame(parent_frame, fg_color="transparent")
                row_frame.pack(fill="x", pady=5)
            self.create_card(row_frame, option, selected_list)

    def add_custom_option(self, option, selected_list):
        """Add a custom option to the selected list."""
        option = option.strip()  # Trim extra spaces
        if not option:
            messagebox.showerror("Error", "Option cannot be empty!")
            return

        # Check for duplicates in the specific list
        if option in selected_list:
            messagebox.showerror("Error", f"{option} already exists!")
            return

        # Add the option to the selected list
        selected_list.append(option)

        # Find the last row frame in the corresponding frame
        parent_frame = (
            self.hobbies_frame
            if selected_list == self.user_data["Hobbies"]
            else self.interests_frame
        )
        last_row = (
            parent_frame.winfo_children()[-1] if parent_frame.winfo_children() else None
        )

        # Check if the last row has space for more cards
        if (
            last_row and len(last_row.winfo_children()) < 4
        ):  # Assuming max 4 cards per row
            self.create_card(last_row, option, selected_list)
        else:
            # Create a new row if the last row is full or doesn't exist
            new_row_frame = ctk.CTkFrame(parent_frame, fg_color="transparent")
            new_row_frame.pack(fill="x", pady=5)
            self.create_card(new_row_frame, option, selected_list)

        # Clear the input field
        if selected_list == self.user_data["Hobbies"]:
            self.hobbies_entry.set("")
        elif selected_list == self.user_data["Interests"]:
            self.interests_entry.set("")

    def add_navigation_buttons(
        self, parent, back_command=None, next_command=None, finish_command=None
    ):
        """Add Back, Next, and Finish buttons centered at the bottom."""
        button_frame = ctk.CTkFrame(parent, fg_color="transparent")
        button_frame.pack(pady=20, fill="x")

        if back_command:
            ctk.CTkButton(
                button_frame, text="Back", command=back_command, fg_color="#2d3142"
            ).pack(side="left", padx=5)
        if next_command:
            # Adjust margin for the "Next" button specifically for step 1
            padx_value = 5 if next_command.__code__.co_consts[0] == 1 else 5
            ctk.CTkButton(
                button_frame, text="Next", command=next_command, fg_color="#2d3142"
            ).pack(side="right", padx=padx_value)
        if finish_command:
            ctk.CTkButton(
                button_frame, text="Finish", command=finish_command, fg_color="#2d3142"
            ).pack(side="right", padx=5)

        # Center align buttons
        button_frame.pack_propagate(False)
        button_frame.update()
        button_frame.pack_configure(pady=(0, 10))

    def show_step(self, index):
        """Show a specific step."""
        if 0 <= index < len(self.steps):
            # Hide the current step
            if self.current_step is not None:
                self.steps[self.current_step].pack_forget()

            # Perform specific actions for each step
            if index == 0:
                self.geometry("600x530")  # Set size for step 1
            elif index == 1:
                self.geometry("600x600")  # Set size for step 2
            elif index == 2:
                self.geometry("700x550")  # Set size for step 3
                self.collect_visible_cards()
                self.initialize_chatbot_state()
                if self.flag == 0:
                    self.start_chatbot()  # Ensure the bot uses updated preferences
            elif index == 3:
                self.geometry("650x500")  # Set size for step 4

            # Show the selected step
            self.steps[index].pack(
                side="right", fill="both", expand=True, padx=5, pady=5
            )

            # Update the sidebar indicators
            for i, step_label in enumerate(self.step_labels):
                step_label.configure(text_color="#f0f0f0" if i == index else "#9c9c9c")

            self.current_step = index

    def finish_registration(self):
        """Handle form completion."""
        required_fields = ["First Name", "Email"]
        for field, var in self.user_data.items():
            if isinstance(var, ctk.StringVar) and not var.get().strip():
                messagebox.showerror("Error", f"{field} is required!")
                return

        # Check if the user agreed to the terms
        if not self.agreed_to_terms.get():
            messagebox.showerror(
                "Error", "You must agree to the terms and conditions to proceed."
            )
            return

        # Collect visible cards to update hobbies and interests
        self.collect_visible_cards()

        for category in ["Responses for Hobbies", "Responses for Interests"]:
            if category not in self.user_data:
                self.user_data[category] = (
                    []
                )  # Initialize as an empty list if no responses are collected

        # Prepare the data for JSON serialization
        serializable_data = {
            key: value.get() if isinstance(value, ctk.StringVar) else value
            for key, value in self.user_data.items()
        }
        serializable_data["registered"] = True  # Set the registered flag

        # Save data in the database
        # try:
        #     user_id = insert_user_data(
        #         serializable_data
        #     )  # Update to return the user ID
        #     messagebox.showinfo(
        #         "Success", "Setup complete! Your preferences have been saved."
        #     )

        #     # Save the user_id locally
        #     with open(LOCAL_STORAGE_FILE, "w") as f:
        #         json.dump({"user_id": user_id}, f)

        #     self.destroy()

        #     # Call the callback function if provided
        #     if self.on_registration_complete:
        #         self.on_registration_complete()

        # except Exception as e:
        #     messagebox.showerror("Error", f"An error occurred while saving data: {e}")

        try:
            user_id = insert_user_data(serializable_data)
            token = jwt.encode({"user_id": user_id}, self.jwt_secret, algorithm="HS256")

            messagebox.showinfo(
                "Success", "Setup complete! Your preferences have been saved."
            )

            # 7) Save the token, not the raw ID
            with open(LOCAL_STORAGE_FILE, "w") as f:
                json.dump({"token": token}, f)

            copy_to_internal(LOCAL_STORAGE_FILE)

            self.destroy()
            if self.on_registration_complete:
                self.on_registration_complete()

        except Exception as e:
            messagebox.showerror("Error", f"An error occurred while saving data: {e}")

    def generate_tag(self, question, response):
        """Generate a tag for a given response using OpenAI."""
        prompt = f"""
        Given the question "{question}" and the response "{response}", categorize the response with a suitable tag such as 'Favorite Team', 'Preferred Cuisine', etc.
        Provide only the tag as output.
        """
        try:
            response = openai.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=20,
                temperature=0.5,
            )
            tag = response.choices[0].message.content.strip()
            return tag
        except Exception as e:
            print(f"Error generating tag: {e}")
            return "Unknown"


if __name__ == "__main__":
    ctk.set_appearance_mode("light")

    app = RegistrationWizard()
    app.mainloop()
