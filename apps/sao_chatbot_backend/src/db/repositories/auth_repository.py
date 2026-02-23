from passlib.context import CryptContext
from src.db.connection import get_db_connection

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AuthRepository:

    def __init__(self):
        self.conn = get_db_connection()

    # ===== HASH =====
    def hash_password(self, password: str) -> str:
        return pwd_context.hash(password[:72])  # กัน bcrypt limit

    # ===== VERIFY =====
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        return pwd_context.verify(plain_password[:72], hashed_password)

    # ===== AUTHENTICATE =====
    def authenticate_user(self, username: str, password: str):
        cur = self.conn.cursor()

        query = """
        SELECT id, username, password, role, is_active
        FROM users
        WHERE username = %s
        """

        cur.execute(query, (username,))
        row = cur.fetchone()

        if not row:
            return None

        user = {
            "id": str(row[0]),
            "username": row[1],
            "password": row[2],
            "role": row[3],
            "is_active": row[4],
        }

        #  inactive user
        if not user["is_active"]:
            return None

        #  password mismatch
        if not self.verify_password(password, user["password"]):
            return None

        return user

    # ===== GET USER =====
    def get_user_by_username(self, username: str):
        cur = self.conn.cursor()

        cur.execute(
            "SELECT id, username, role, is_active FROM users WHERE username = %s",
            (username,)
        )

        row = cur.fetchone()

        if not row:
            return None

        return {
            "id": str(row[0]),
            "username": row[1],
            "role": row[2],
            "is_active": row[3],
        }
    def get_all_users(self, limit: int = 50, offset: int = 0):
        cur = self.conn.cursor()

        query = """
        SELECT id, username, role, is_active
        FROM users
        ORDER BY created_at DESC
        LIMIT %s OFFSET %s
        """

        cur.execute(query, (limit, offset))
        rows = cur.fetchall()

        return [
            {
                "id": str(row[0]),
                "username": row[1],
                "role": row[2],
                "is_active": row[3],
            }
            for row in rows
        ]

    # ===== CREATE USER =====
    def create_user(self, username: str, password: str, role: str):
        cur = self.conn.cursor()

        hashed_password = self.hash_password(password)

        query = """
        INSERT INTO users (username, password, role, is_active)
        VALUES (%s, %s, %s, TRUE)
        RETURNING id, username, role
        """

        cur.execute(query, (username, hashed_password, role))
        self.conn.commit()

        row = cur.fetchone()

        return {
            "id": str(row[0]),
            "username": row[1],
            "role": row[2],
        }

    # ===== UPDATE USER =====
    def update_user(self, user_id: str, username: str, password: str, role: str):
        cur = self.conn.cursor()

        hashed_password = self.hash_password(password)

        query = """
        UPDATE users
        SET username = %s,
            password = %s,
            role = %s,
            updated_at = NOW()
        WHERE id = %s
        RETURNING id, username, role
        """

        cur.execute(query, (username, hashed_password, role, user_id))
        self.conn.commit()

        row = cur.fetchone()

        if not row:
            return None

        return {
            "id": str(row[0]),
            "username": row[1],
            "role": row[2],
        }

    # ===== DELETE USER =====
    def delete_user(self, user_id: str):
        cur = self.conn.cursor()

        query = "DELETE FROM users WHERE id = %s RETURNING id"
        cur.execute(query, (user_id,))
        self.conn.commit()

        row = cur.fetchone()

        return {"deleted_id": str(row[0])} if row else None