import json
from typing import List, Tuple

from src.db.connection import get_db_connection


class ChatRepository:
    def save_message(self, user_id: int, session_id: str, user_msg: str, ai_msg: str, context: list = None):
        conn = None
        try:
            conn = get_db_connection()
            conn.autocommit = True
            cur = conn.cursor()
            
            query = """
                INSERT INTO conversations 
                (user_id, session_id, user_message, ai_message, retrieval_context)
                VALUES (%s, %s, %s, %s, %s)
            """
            cur.execute(query, (
                user_id, 
                session_id, 
                user_msg, 
                ai_msg, 
                json.dumps(context or [])
            ))
            cur.close()
        except Exception as e:
            print(f"❌ DB Insert Error: {e}")
            raise e
        finally:
            if conn: conn.close()

    def get_messages_by_session(self, user_id: int, session_id: str) -> List[Tuple]:
        """
        Fetches raw rows (user_msg, ai_msg, created_at) for a specific session.
        """
        conn = None
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            
            query = """
                SELECT user_message, ai_message, created_at
                FROM conversations
                WHERE user_id = %s AND session_id = %s
                ORDER BY created_at ASC
            """
            cur.execute(query, (user_id, session_id))
            rows = cur.fetchall()
            cur.close()
            return rows
        except Exception as e:
            print(f"DB Fetch Error: {e}")
            return []
        finally:
            if conn: conn.close()

    def get_user_sessions_summary(self, user_id: int) -> List[Tuple]:
        """Fetches unique sessions for the sidebar list."""
        conn = None
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            
            query = """
                SELECT DISTINCT ON (session_id) 
                    session_id, 
                    user_message, 
                    created_at
                FROM conversations
                WHERE user_id = %s
                ORDER BY session_id, created_at ASC
            """
            cur.execute(query, (user_id,))
            rows = cur.fetchall()
            cur.close()
            return rows
        except Exception as e:
            print(f"DB Session Fetch Error: {e}")
            return []
        finally:
            if conn: conn.close()