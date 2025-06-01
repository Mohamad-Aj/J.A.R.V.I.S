import psycopg2
import uuid

DATABASE_URL = "postgresql://postgres:Jarvisgroup15@db.nsgeslmkrejtlifazhnu.supabase.co:5432/postgres"
DATABASE_URL = "postgresql://postgres.nsgeslmkrejtlifazhnu:Jarvisgroup15@aws-0-eu-central-1.pooler.supabase.com:6543/postgres"


def insert_user_data(user_data):
    """Insert user data into the database."""
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        print("Connected to the database!")

        # Insert into users table
        user_id = str(uuid.uuid4())  # Generate a unique user ID
        cursor.execute(
            """
            INSERT INTO users (
                id, first_name, last_name, email, phone, street_name, house_apartment, city, state, zip_code, country, date_of_birth
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
            (
                user_id,
                user_data["First Name"],
                user_data["Last Name"],
                user_data["Email"],
                user_data["Phone"],
                user_data["Street Name"],
                user_data["House/Apartment"],
                user_data["City"],
                user_data["State"],
                user_data["Zip Code"],
                user_data["Country"],
                user_data["Date of Birth"],
            ),
        )

        # Insert into hobbies table
        for hobby in user_data["Hobbies"]:
            cursor.execute(
                """
                INSERT INTO hobbies (user_id, hobby) VALUES (%s, %s)
            """,
                (user_id, hobby),
            )

        # Insert into interests table
        for interest in user_data["Interests"]:
            cursor.execute(
                """
                INSERT INTO interests (user_id, interest) VALUES (%s, %s)
            """,
                (user_id, interest),
            )

        # Insert into hobby_responses table
        for i, response in enumerate(user_data["Responses for Hobbies"]):
            cursor.execute(
                """
                INSERT INTO hobby_responses (user_id, hobby, tag, answer) VALUES (%s, %s, %s, %s)
            """,
                (
                    user_id,
                    user_data["Hobbies"][i // 3],  # Assign hobby by index
                    response["Tag"],
                    response["Answer"],
                ),
            )

        # Insert into interest_responses table
        for i, response in enumerate(user_data["Responses for Interests"]):
            cursor.execute(
                """
                INSERT INTO interest_responses (user_id, interest, tag, answer) VALUES (%s, %s, %s, %s)
            """,
                (
                    user_id,
                    user_data["Interests"][i // 3],  # Assign interest by index
                    response["Tag"],
                    response["Answer"],
                ),
            )

        conn.commit()
        print("Data inserted successfully!")
        return user_id

    except Exception as e:
        print(f"An error occurred: {e}")

    finally:
        if conn:
            cursor.close()
            conn.close()
