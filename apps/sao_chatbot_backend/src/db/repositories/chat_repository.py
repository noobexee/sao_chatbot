import json
from typing import List, Tuple, Optional, Dict
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

    def get_user_sessions_summary(self, user_id: int) -> List[Dict]:
        """
        Fetches unique sessions for the sidebar list, including metadata (Rename/Pin).
        """
        conn = None
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            
            # CRITICAL FIX: Select custom_title and is_pinned
            query = """
                SELECT DISTINCT ON (session_id) 
                    session_id, 
                    COALESCE(custom_title, user_message) as title, 
                    created_at,
                    COALESCE(is_pinned, FALSE) as is_pinned
                FROM conversations
                WHERE user_id = %s
                ORDER BY session_id, is_pinned DESC, custom_title DESC NULLS LAST, created_at ASC
            """
            cur.execute(query, (user_id,))
            rows = cur.fetchall()
            
            # Convert to Dictionary for Frontend
            results = []
            for row in rows:
                results.append({
                    "session_id": str(row[0]),
                    "title": row[1],
                    "created_at": row[2],
                    "is_pinned": row[3]
                })
            
            # Sort: Pinned first (True), then Newest first
            results.sort(key=lambda x: (x['is_pinned'], x['created_at']), reverse=True)
            
            cur.close()
            return results
        except Exception as e:
            print(f"DB Session Fetch Error: {e}")
            return []
        finally:
            if conn: conn.close()

    def delete_session(self, user_id: int, session_id: str) -> bool:
        conn = None
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            
            query = "DELETE FROM conversations WHERE user_id = %s AND session_id = %s"
            cur.execute(query, (user_id, session_id))
            conn.commit()
            
            cur.close()
            return True
        except Exception as e:
            print(f"Error deleting session in DB: {e}")
            if conn:
                conn.rollback()
            return False
        finally:
            if conn: conn.close()

    def update_session_metadata(self, user_id: int, session_id: str, title: Optional[str] = None, is_pinned: Optional[bool] = None) -> bool:
        """
        Updates metadata for ALL rows in a session to keep them consistent.
        """
        conn = None
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            
            updates = []
            params = []
            
            if title is not None:
                updates.append("custom_title = %s")
                params.append(title)
            
            if is_pinned is not None:
                updates.append("is_pinned = %s")
                params.append(is_pinned)
            
            if not updates:
                return False

            query = f"UPDATE conversations SET {', '.join(updates)} WHERE session_id = %s AND user_id = %s"
            params.extend([session_id, user_id])
            
            cur.execute(query, tuple(params))
            conn.commit()
            
            cur.close()
            return True
        except Exception as e:
            print(f"Error updating metadata: {e}")
            if conn: conn.rollback()
            return False
        finally:
            if conn: conn.close()