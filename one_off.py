import sqlite3

# Database path (modify if needed)
DB_PATH = "/serverbot/server_logs.db"

def initialize_database():
    """Create required tables if they don't exist."""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        # Create credentials table for storing the bot token
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS credentials (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key TEXT UNIQUE NOT NULL,
                value TEXT NOT NULL
            )
        """)
        # Create table for storing authorized users
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS authorized_users (
                user_id INTEGER PRIMARY KEY,
                role TEXT NOT NULL CHECK(role IN ('admin', 'standard'))
            )
        """)
        conn.commit()

def store_bot_token(token):
    """Store the Telegram bot token in the database."""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO credentials (key, value) VALUES ('bot_token', ?)", (token,))
        conn.commit()
    print("✅ Bot token stored successfully.")

def add_authorized_user(user_id, role="standard"):
    """Add an authorized user to the database."""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO authorized_users (user_id, role) VALUES (?, ?)", (user_id, role))
        conn.commit()
    print(f"✅ User {user_id} added as {role}.")


def store_plex_token(token):
    """Store the Plex token securely in the database."""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO credentials (key, value) VALUES ('plex_token', ?)", (token,))
        conn.commit()
    print("✅ Plex token stored successfully.")


def display_database_contents():
    """Display stored data for verification."""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        print("\n🔹 Stored Bot Token:")
        cursor.execute("SELECT value FROM credentials WHERE key='bot_token'")
        result = cursor.fetchone()
        if result:
            print(f"   Token: {result[0][:5]}... (hidden for security)")
        else:
            print("   No token found.")

        print("\n🔹 Authorized Users:")
        cursor.execute("SELECT user_id, role FROM authorized_users")
        users = cursor.fetchall()
        if users:
            for user in users:
                print(f"   - User ID: {user[0]}, Role: {user[1]}")
        else:
            print("   No users found.")

if __name__ == "__main__":
    # Initialize tables
    initialize_database()

    # Store your bot token securely (change this before running)
    store_bot_token("enter_token_from_bot_father")

    # Add authorized users (change IDs as needed)
    add_authorized_user(987654321, "admin")  # Example admin, USE YOUR USER ID HERE,
    add_authorized_user(123456789, "standard")  # Example standard user (say you want to share the bot with you friend, put their id here)

    store_plex_token("enter_plex_token")  # Replace with your actual token

    # Display contents for verification
    display_database_contents()
