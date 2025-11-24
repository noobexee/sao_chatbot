import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

def create_user():
    db_url = os.getenv("SQL_DATABASE_URL")
    if not db_url:
        print("❌ Error: DATABASE_URL is missing from .env")
        return

    try:
        conn = psycopg2.connect(db_url)
        cur = conn.cursor()
        
        TEST_USERNAME = "test_user"
        TEST_PASSWORD = "password123"

        cur.execute("SELECT id FROM users WHERE username = %s", (TEST_USERNAME,))
        existing_user = cur.fetchone()

        if existing_user:
            print(f"⚠️  User '{TEST_USERNAME}' already exists (ID: {existing_user[0]}). Skipping creation.")
        else:

            insert_query = """
            INSERT INTO users (username, password) 
            VALUES (%s, %s) 
            RETURNING id;
            """
            cur.execute(insert_query, (TEST_USERNAME, TEST_PASSWORD))
            
            conn.commit()
            
            new_id = cur.fetchone()[0]
            print(f"✅ Success! Created user.")
            print(f"   ID: {new_id}")
            print(f"   Username: {TEST_USERNAME}")
            print(f"   Password: {TEST_PASSWORD}")

    except Exception as e:
        print(f"❌ Database Error: {e}")
    finally:
        if 'conn' in locals() and conn:
            cur.close()
            conn.close()

if __name__ == "__main__":
    create_user()