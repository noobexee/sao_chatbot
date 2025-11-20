import json
import os
import psycopg2
from src.api.v1.models.rag_response import RAGResponse
from src.app.services.llm_manager import get_llm

class RAGService:
    def __init__(self):
        self.llm = get_llm()
        self.db_url = os.getenv("SQL_DATABASE_URL")

    def _get_db_connection(self):
        if not self.db_url:
            print("⚠️ Warning: DATABASE_URL is not set.")
            return None
        return psycopg2.connect(self.db_url)

    def save_to_history(self, user_id: int, session_id: str, query: str, answer: str):
        conn = None
        try:
            conn = self._get_db_connection()
            if not conn:
                return

            conn.autocommit = True 
            cur = conn.cursor()

            insert_query = """
                INSERT INTO conversations 
                (user_id, session_id, user_message, ai_message, retrieval_context)
                VALUES (%s, %s, %s, %s, %s)
            """
            
            cur.execute(insert_query, (
                user_id, 
                session_id, 
                query, 
                answer, 
                json.dumps([]) 
            ))
            
            print("🔥 DEBUG: Insert executed successfully!") 
            cur.close()

        except Exception as e:
            print(f"ERROR SAVING TO DB: {e}")
        finally:
            if conn:
                conn.close()

    def get_user_sessions(self, user_id: int) -> list:
        """
        Returns a list of chat sessions for the user to display in the sidebar.
        Uses the FIRST user message as the 'Title' of the chat.
        """
        conn = None
        sessions = []
        try:
            conn = self._get_db_connection()
            if not conn: return []
            
            cur = conn.cursor()
            
            query = """
                SELECT DISTINCT ON (session_id) 
                    session_id, 
                    user_message as title, 
                    created_at
                FROM conversations
                WHERE user_id = %s
                ORDER BY session_id, created_at ASC
            """
            cur.execute(query, (user_id,))
            rows = cur.fetchall()
            
            for row in rows:
                sessions.append({
                    "session_id": str(row[0]),
                    "title": row[1][:50] + "..." if len(row[1]) > 50 else row[1], 
                    "created_at": row[2].isoformat()
                })
            
            sessions.sort(key=lambda x: x['created_at'], reverse=True)
            
            cur.close()
        except Exception as e:
            print(f"❌ Failed to fetch sessions: {e}")
        finally:
            if conn: conn.close()
        return sessions

    def get_session_history(self, user_id: int, session_id: str) -> list:
        """
        Returns the full message history for a specific session ID.
        """
        conn = None
        messages = []
        try:
            conn = self._get_db_connection()
            if not conn: return []
            
            cur = conn.cursor()
            
            query = """
                SELECT user_message, ai_message, created_at
                FROM conversations
                WHERE user_id = %s AND session_id = %s
                ORDER BY created_at ASC
            """
            cur.execute(query, (user_id, session_id))
            rows = cur.fetchall()
            
            for row in rows:
                timestamp = row[2].isoformat()
                
                messages.append({"role": "user", "content": row[0], "created_at": timestamp})
                messages.append({"role": "assistant", "content": row[1], "created_at": timestamp})
            
            cur.close()
        except Exception as e:
            print(f"❌ Failed to fetch history: {e}")
        finally:
            if conn: conn.close()
        return messages

    # --- RAG LOGIC ---
    async def answer_question(self, user_id: int, session_id: str, query: str) -> RAGResponse:
        prompt = query
        answer = self.llm.invoke(prompt=prompt)
        answer_text = str(answer)

        self.save_to_history(user_id, session_id, query, answer_text)

        return RAGResponse(answer=answer_text, model_used=self.llm.__class__.__name__)

rag_service = RAGService()