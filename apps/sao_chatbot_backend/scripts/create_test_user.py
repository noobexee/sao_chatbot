import os
import psycopg2
from dotenv import load_dotenv
from passlib.context import CryptContext

load_dotenv()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password[:72])  # กัน bcrypt limit


def create_user():
    db_url = os.getenv("SQL_DATABASE_URL")
    if not db_url:
        print("Error: SQL_DATABASE_URL is missing from .env")
        return

    try:
        conn = psycopg2.connect(db_url)
        cur = conn.cursor()

        USERNAME = "test_user"
        PASSWORD = "password123"
        ROLE = "user"  # 👉 เปลี่ยนได้: user / admin / document_manager

        # check existing
        cur.execute("SELECT id FROM users WHERE username = %s", (USERNAME,))
        existing_user = cur.fetchone()

        if existing_user:
            print(f"User '{USERNAME}' already exists (ID: {existing_user[0]})")
            return

        hashed_password = hash_password(PASSWORD)

        insert_query = """
        INSERT INTO users (username, password, role, is_active, created_at, updated_at)
        VALUES (%s, %s, %s, %s, NOW(), NOW())
        RETURNING id;
        """

        cur.execute(insert_query, (
            USERNAME,
            hashed_password,
            ROLE,
            True
        ))

        new_id = cur.fetchone()[0]
        conn.commit()

        print("✅ User created successfully!")
        print(f"   ID: {new_id}")
        print(f"   Username: {USERNAME}")
        print(f"   Role: {ROLE}")

    except Exception as e:
        print(f"Database Error: {e}")

    finally:
        if 'conn' in locals() and conn:
            cur.close()
            conn.close()


if __name__ == "__main__":
    create_user()