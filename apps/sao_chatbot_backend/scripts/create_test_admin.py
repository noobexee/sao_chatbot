import os
import psycopg2
from dotenv import load_dotenv
from passlib.context import CryptContext

load_dotenv()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str):
    return pwd_context.hash(password)


def create_admin():
    db_url = os.getenv("SQL_DATABASE_URL")

    if not db_url:
        print("Error: SQL_DATABASE_URL is missing from .env")
        return

    try:
        conn = psycopg2.connect(db_url)
        cur = conn.cursor()

        ADMIN_USERNAME = "admin"
        ADMIN_PASSWORD = "admin123"  # 🔥 เปลี่ยนตอนใช้งานจริง

        # check existing
        cur.execute("SELECT id FROM users WHERE username = %s", (ADMIN_USERNAME,))
        existing_user = cur.fetchone()

        if existing_user:
            print(f"Admin already exists (ID: {existing_user[0]})")
            return

        hashed_password = hash_password(ADMIN_PASSWORD)

        insert_query = """
        INSERT INTO users (username, password, role, is_active)
        VALUES (%s, %s, %s, %s)
        RETURNING id;
        """

        cur.execute(insert_query, (
            ADMIN_USERNAME,
            hashed_password,
            "admin",
            True
        ))

        conn.commit()
        new_id = cur.fetchone()[0]

        print("✅ Admin created successfully!")
        print(f"   ID: {new_id}")
        print(f"   Username: {ADMIN_USERNAME}")
        print(f"   Password: {ADMIN_PASSWORD}")

    except Exception as e:
        print(f"Database Error: {e}")

    finally:
        if 'conn' in locals() and conn:
            cur.close()
            conn.close()


if __name__ == "__main__":
    create_admin()