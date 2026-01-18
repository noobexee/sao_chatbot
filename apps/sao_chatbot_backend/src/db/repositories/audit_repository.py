import json
from src.db.connection import get_db_connection

class AuditRepository:
    
    def save_audit_session(self, audit_id: str, file_name: str, file_content: bytes) -> bool:
        print(f"   [DB] Attempting to save session: ID={audit_id}, File={file_name}, Size={len(file_content)} bytes")
        conn = None
        try:
            conn = get_db_connection()
            cur = conn.cursor()

            query_session = """
                INSERT INTO audit_sessions (audit_id, file_name, file_data, created_at)
                VALUES (%s, %s, %s, NOW())
                ON CONFLICT (audit_id) 
                DO UPDATE SET 
                    file_name = EXCLUDED.file_name,
                    file_data = EXCLUDED.file_data;
            """
            cur.execute(query_session, (audit_id, file_name, file_content))
            
            conn.commit()
            cur.close()
            return True
        except Exception as e:
            if conn: conn.rollback()
            raise e
        finally:
            if conn: conn.close()
    def save_step_log(self, audit_id: str, step_id: int, ai_result: dict, feedback: str = None) -> bool:
        """
        Save ONLY the AI output data for a specific step to audit_feedback_logs.
        Enhanced to handle Structured State Pattern AND Result Correctness Logic (BOOLEAN).
        """
        print(f"   [DB] Saving Step Log: AuditID={audit_id}, Step={step_id}, Feedback={feedback}")
        conn = None
        try:
            conn = get_db_connection()
            cur = conn.cursor()

            query_log = """
                INSERT INTO audit_feedback_logs 
                (audit_id, criteria_id, field_type, ai_value, user_edit, user_value, result_correct, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
            """

            # --- Logic คำนวณ result_correct (Boolean) ---
            default_correctness = False if feedback == 'down' else True

            # --- Logic สำหรับ Step 4 ---
            if step_id == 4:
                details = ai_result.get('details', {})
                
                # --- FIX: Handle if details is NOT a dict (e.g. List or None) ---
                if isinstance(details, list):
                    print(f"   ⚠️ [DB] Warning: 'details' received as LIST, not DICT. Converting/Ignoring.")
                    # If it's a list, we can't process keys. 
                    # Attempt to convert if it's a list of key-value pairs, or just log error.
                    # For now, let's treat it as empty or log it.
                    # You might want to debug WHY it is a list.
                    details = {} 
                elif not isinstance(details, dict):
                    details = {}

                print(f"   [DB] Processing Step 4 Details: {len(details)} fields")
                
                for key, item in details.items():
                    # ตรวจสอบว่าเป็น Structured Object แบบใหม่หรือไม่
                    if isinstance(item, dict) and 'original' in item:
                        ai_val = str(item['original']) if item['original'] is not None else ""
                        is_edited = bool(item.get('isEdited', False))
                        user_val = str(item['value']) if (is_edited and item['value'] is not None) else ""
                        
                        result_correct = False if is_edited else default_correctness

                        cur.execute(query_log, (
                            audit_id, 
                            4,              # criteria_id
                            key,            # field_type
                            ai_val,         # ai_value
                            is_edited,      # user_edit
                            user_val,       # user_value
                            result_correct  # result_correct (Boolean)
                        ))
                    else:
                        # Fallback
                        cur.execute(query_log, (
                            audit_id, 
                            4, key, 
                            str(item),      
                            False, "", 
                            default_correctness
                        ))

            # --- Logic สำหรับ Step 6 ---
            elif step_id == 6:
                people = ai_result.get('people', [])
                print(f"   [DB] Processing Step 6 People: Found {len(people)} people")
                
                result_correct = default_correctness
                
                cur.execute(query_log, (
                    audit_id,
                    6,              # criteria_id
                    "people_list",  # field_type
                    str(people),    # ai_value
                    False, "",      # user_edit
                    result_correct  # result_correct
                ))

            # --- Logic สำหรับ Step อื่นๆ ---
            else:
                print(f"   [DB] Processing Generic Step {step_id}")
                cur.execute(query_log, (
                    audit_id,
                    step_id,
                    "raw_result",
                    json.dumps(ai_result, ensure_ascii=False),
                    False, "", 
                    default_correctness
                ))

            conn.commit()
            cur.close()
            print("   [DB] Step Log Saved Successfully.")
            return True

        except Exception as e:
            print(f"   ❌ [DB] AI Log Insert Error: {e}")
            if conn: conn.rollback()
            return False 
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

    def get_audit_file_content(self, audit_id: str):
        """ดึงเนื้อไฟล์ Binary ออกมาเพื่อส่งกลับไปให้ Frontend แสดงผล"""
        conn = None
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            # ดึงเฉพาะ file_data
            query = "SELECT file_data FROM audit_sessions WHERE audit_id = %s"
            cur.execute(query, (audit_id,))
            row = cur.fetchone()
            cur.close()
            if row:
                return row[0] # คืนค่าเป็น bytes
            return None
        except Exception as e:
            print(f"DB File Fetch Error: {e}")
            return None
        finally:
            if conn: conn.close()