import json
from src.db.connection import get_db_connection

class InitialReviewRepository:
    
    def save_criteria_log(self, InitialReview_id: str, criteria_id: int, ai_result: dict, feedback: str = None) -> bool:
        """
        Save ONLY the AI output data for a specific criteria to InitialReview_feedback_logs.
        Enhanced to handle Structured State Pattern AND Result Correctness Logic (BOOLEAN).
        """
        print(f"   [DB] Saving criteria Log: InitialReviewID={InitialReview_id}, criteria={criteria_id}, Feedback={feedback}")
        conn = None
        try:
            conn = get_db_connection()
            cur = conn.cursor()

            query_log = """
                INSERT INTO InitialReview_feedback_logs 
                (InitialReview_id, criteria_id, field_type, ai_value, user_edit, user_value, result_correct, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
            """

            # --- Logic คำนวณ result_correct (Boolean) ---
            # Default: If feedback is 'down' (thumbs down), it's False. Otherwise True.
            default_correctness = False if feedback == 'down' else True

            # --- Logic สำหรับ criteria 4 ---
            if criteria_id == 4:
                details = ai_result.get('details', {})
                
                if isinstance(details, list):
                    print(f"   ⚠️ [DB] Warning: 'details' received as LIST, not DICT. Converting/Ignoring.")
                    details = {} 
                elif not isinstance(details, dict):
                    details = {}

                print(f"   [DB] Processing criteria 4 Details: {len(details)} fields")
                
                for key, item in details.items():
                    # ตรวจสอบว่าเป็น Structured Object แบบใหม่หรือไม่
                    if isinstance(item, dict) and 'original' in item:
                        ai_val = str(item['original']) if item['original'] is not None else ""
                        is_edited = bool(item.get('isEdited', False))
                        user_val = str(item['value']) if (is_edited and item['value'] is not None) else ""
                        
                        # If user edited, it implies AI was wrong (False). If not edited, use default (True/False based on feedback)
                        result_correct = False if is_edited else default_correctness

                        cur.execute(query_log, (
                            InitialReview_id, 
                            4,              # criteria_id
                            key,            # field_type
                            ai_val,         # ai_value
                            is_edited,      # user_edit
                            user_val,       # user_value
                            result_correct  # result_correct (Boolean)
                        ))
                    else:
                        # Fallback for old format
                        cur.execute(query_log, (
                            InitialReview_id, 
                            4, key, 
                            str(item),      
                            False, "", 
                            default_correctness
                        ))

            # --- Logic สำหรับ criteria 6 ---
            elif criteria_id == 6:
                people = ai_result.get('people', [])
                print(f"   [DB] Processing criteria 6 People: Found {len(people)} people")
                
                result_correct = default_correctness
                
                # Use json.dumps for complex objects to ensure valid string format
                ai_value_str = json.dumps(people, ensure_ascii=False)

                cur.execute(query_log, (
                    InitialReview_id,
                    6,              # criteria_id
                    "people_list",  # field_type
                    ai_value_str,   # ai_value
                    False, "",      # user_edit
                    result_correct  # result_correct
                ))

            # --- Logic สำหรับ criteria อื่นๆ ---
            else:
                print(f"   [DB] Processing Generic criteria {criteria_id}")
                cur.execute(query_log, (
                    InitialReview_id,
                    criteria_id,
                    "raw_result",
                    json.dumps(ai_result, ensure_ascii=False),
                    False, "", 
                    default_correctness
                ))

            conn.commit()
            cur.close()
            print("   [DB] criteria Log Saved Successfully.")
            return True

        except Exception as e:
            print(f"   ❌ [DB] AI Log Insert Error: {e}")
            if conn: conn.rollback()
            return False 
        finally:
            if conn: conn.close()

    def get_InitialReview_summary(self, InitialReview_id: str) -> dict:
        conn = None
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            query = "SELECT * FROM InitialReview_sessions WHERE InitialReview_id = %s"
            cur.execute(query, (InitialReview_id,))
            row = cur.fetchone()
            cur.close()
            if row:
                return {"InitialReview_id": row[0], "file_name": row[1], "created_at": str(row[2])}
            return {}
        except Exception as e:
            print(f"DB Fetch Error: {e}")
            return {}
        finally:
            if conn: conn.close()