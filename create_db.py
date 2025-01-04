import psycopg2

DATABASE_URL = "postgresql://postgres:Jarvisgroup15@db.nsgeslmkrejtlifazhnu.supabase.co:5432/postgres"

# Establish connection
try:
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()
    print("Connected to the database!")

    # Create tables
    cursor.execute("""
    -- Users table
    CREATE TABLE IF NOT EXISTS users (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        first_name TEXT,
        last_name TEXT,
        email TEXT UNIQUE NOT NULL,
        phone TEXT,
        street_name TEXT,
        house_apartment TEXT,
        city TEXT,
        state TEXT,
        zip_code TEXT,
        country TEXT,
        date_of_birth DATE,
        gender TEXT
    );

    -- Hobbies table
    CREATE TABLE IF NOT EXISTS hobbies (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        user_id UUID REFERENCES users(id) ON DELETE CASCADE,
        hobby TEXT
    );

    -- Interests table
    CREATE TABLE IF NOT EXISTS interests (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        user_id UUID REFERENCES users(id) ON DELETE CASCADE,
        interest TEXT
    );

    -- Hobby responses table
    CREATE TABLE IF NOT EXISTS hobby_responses (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        user_id UUID REFERENCES users(id) ON DELETE CASCADE,
        hobby TEXT,
        tag TEXT,
        answer TEXT
    );

    -- Interest responses table
    CREATE TABLE IF NOT EXISTS interest_responses (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        user_id UUID REFERENCES users(id) ON DELETE CASCADE,
        interest TEXT,
        tag TEXT,
        answer TEXT
    );
    """)

    conn.commit()
    print("Tables created successfully!")

except Exception as e:
    print(f"An error occurred: {e}")

finally:
    if conn:
        cursor.close()
        conn.close()
