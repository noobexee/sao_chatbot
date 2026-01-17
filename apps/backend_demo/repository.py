import psycopg2
import json
from db import get_db_connection

class AuditRepository:
    
    def save_audit_session(self, audit_id: str, file_name: str) -> bool:
        """
        Saves ONLY the audit session (audit_id, file_name).
        """
        print(f"   [DB] Attempting to save session: ID={audit_id}, File={file_name}")
        conn = None
        try:
            conn = get_db_connection()
            cur = conn.cursor()

            query_session = """
                INSERT INTO audit_sessions (audit_id, file_name, created_at)
                VALUES (%s, %s, NOW())
                ON CONFLICT (audit_id) DO NOTHING
            """
            cur.execute(query_session, (audit_id, file_name))
            
            conn.commit()
            cur.close()
            print("   [DB] Session Saved Successfully.")
            return True
        except Exception as e:
            print(f"   ❌ [DB] Session Insert Error: {e}")
            if conn: conn.rollback()
            raise e
        finally:
            if conn: conn.close()

    def save_step_log(self, audit_id: str, step_id: int, ai_result: dict) -> bool:
        """
        Save ONLY the AI output data for a specific step to audit_feedback_logs.
        """
        print(f"   [DB] Saving Step Log: AuditID={audit_id}, Step={step_id}")
        conn = None
        try:
            conn = get_db_connection()
            cur = conn.cursor()

            query_log = """
                INSERT INTO audit_feedback_logs 
                (audit_id, criteria_id, field_type, ai_value, user_edit, user_value, result_correct, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
            """

            # --- Logic สำหรับ Step 4 ---
            if step_id == 4:
                details = ai_result.get('details', {})
                print(f"   [DB] Processing Step 4 Details: {len(details)} fields")
                for key, value in details.items():
                    cur.execute(query_log, (
                        audit_id, 
                        4,              # criteria_id
                        key,            # field_type
                        str(value),     # ai_value
                        False, "", None
                    ))

            # --- Logic สำหรับ Step 6 ---
            elif step_id == 6:
                people = ai_result.get('people', [])
                print(f"   [DB] Processing Step 6 People: Found {len(people)} people")
                cur.execute(query_log, (
                    audit_id,
                    6,              # criteria_id
                    "people_list",  # field_type
                    str(people),    # ai_value
                    False, "", None
                ))

            # --- Logic สำหรับ Step อื่นๆ ---
            else:
                print(f"   [DB] Processing Generic Step {step_id}")
                cur.execute(query_log, (
                    audit_id,
                    step_id,
                    "raw_result",
                    json.dumps(ai_result, ensure_ascii=False),
                    False, "", None
                ))

            conn.commit()
            cur.close()
            print("   [DB] Step Log Saved Successfully.")
            return True

        except Exception as e:
            print(f"   ❌ [DB] AI Log Insert Error: {e}")
            if conn: conn.rollback()
            raise e
        finally:
            if conn: conn.close()

    def get_audit_summary(self, audit_id: str) -> dict:
        conn = None
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            query = "SELECT * FROM audit_sessions WHERE audit_id = %s"
            cur.execute(query, (audit_id,))
            row = cur.fetchone()
            cur.close()
            if row:
                return {"audit_id": row[0], "file_name": row[1], "created_at": str(row[2])}
            return {}
        except Exception as e:
            print(f"DB Fetch Error: {e}")
            return {}
        finally:
            if conn: conn.close()