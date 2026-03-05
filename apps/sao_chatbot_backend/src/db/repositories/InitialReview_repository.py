import json
from typing import List, Tuple, Optional, Dict
from src.db.connection import get_db_connection

class InitialReviewRepository:
    
    def save_criteria_log(self, user_id: str, session_id: str, criteria_id: int, ai_result: dict, feedback: str = None) -> bool:
        """
        บันทึก Log ผลการตรวจสอบรายข้อ (Criteria) โดยอิงตาม session_id และ user_id
        """
        print(f"   [DB] Saving Log: User={user_id}, Session={session_id}, Criteria={criteria_id}")
        conn = None
        try:
            conn = get_db_connection()
            cur = conn.cursor()

            query_log = """
                INSERT INTO initial_review_logs 
                (user_id, session_id, criteria_id, field_type, ai_value, user_edit, user_value, result_correct, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW())
            """

            default_correctness = False if feedback == 'down' else True
            if criteria_id == 4:
                details = ai_result.get('details', {})
                for k, v in details.items():
                    if isinstance(v, dict):
                        v_ai = str(v.get('original', '')) if v.get('original') else ""
                        v_user = str(v.get('value', '')) if v.get('value') else ""
                        is_edited = v.get('isEdited', False)
                    else:
                        v_ai = str(v) if v else ""
                        v_user = v_ai
                        is_edited = False

                    cur.execute(query_log, (
                        user_id, session_id, 4, k, v_ai, is_edited, v_user, default_correctness
                    ))

            elif criteria_id in [2, 8]:
                auth_data = ai_result.get('authority', {})
                
                if 'finalResult' in auth_data:
                    ai_res = auth_data.get('aiResult', '')
                    final_res = auth_data.get('finalResult', '')
                    ai_reason = auth_data.get('aiReason', '')
                    final_reason = auth_data.get('finalReason', '')
                    is_overridden = auth_data.get('isOverridden', False)
                    
                    cur.execute(query_log, (
                        user_id, session_id, criteria_id, f"criteria{criteria_id}_result", 
                        ai_res, is_overridden, final_res, not is_overridden
                    ))
                    cur.execute(query_log, (
                        user_id, session_id, criteria_id, f"criteria{criteria_id}_reason", 
                        ai_reason, (ai_reason != final_reason), final_reason, True
                    ))
                else:
                    ai_val = json.dumps(ai_result, ensure_ascii=False)
                    cur.execute(query_log, (
                        user_id, session_id, criteria_id, f"criteria{criteria_id}_raw", 
                        ai_val, False, "", default_correctness
                    ))

            elif criteria_id == 6:
                people = ai_result.get('people', [])
                ai_value_str = json.dumps(people, ensure_ascii=False)

                cur.execute(query_log, (
                    user_id, session_id, 6, "people_list", ai_value_str, False, "", default_correctness
                ))

            else:
                ai_val = json.dumps(ai_result, ensure_ascii=False)
                user_val = ai_result.get('manual_selection', '')
                is_edited = bool(user_val)

                cur.execute(query_log, (
                    user_id, session_id, criteria_id, "raw_result", ai_val, is_edited, user_val, default_correctness
                ))

            conn.commit()
            cur.close()
            return True

        except Exception as e:
            print(f"   ❌ [DB] Log Insert Error: {e}")
            if conn: conn.rollback()
            return False 
        finally:
            if conn: conn.close()
    
    def get_all_sessions(self, user_id: str) -> List[Dict]:
        """ดึงประวัติการตรวจสอบทั้งหมดของ User คนนั้นๆ"""
        conn = None
        try:
            conn = get_db_connection()
            cur = conn.cursor(dictionary=True)

            query = """
                SELECT session_id, MAX(created_at) as last_updated, COUNT(DISTINCT criteria_id) as criteria_count
                FROM initial_review_logs
                WHERE user_id = %s
                GROUP BY session_id
                ORDER BY last_updated DESC
            """
            cur.execute(query, (user_id,))
            rows = cur.fetchall()
            cur.close()
            return rows
        except Exception as e:
            print(f"❌ DB Fetch Error: {e}")
            return []
        finally:
            if conn: conn.close()

    def get_review_by_session(self, user_id: str, session_id: str) -> List[Dict]:
        """ดึงข้อมูล Logs ทั้งหมดภายใต้ Session ID (เอกสารฉบับเดียว)"""
        conn = None
        try:
            conn = get_db_connection()
            cur = conn.cursor(dictionary=True)
            
            query = """
                SELECT criteria_id, field_type, ai_value, user_edit, user_value, result_correct, created_at
                FROM initial_review_logs 
                WHERE user_id = %s AND session_id = %s
                ORDER BY criteria_id ASC, created_at ASC
            """
            cur.execute(query, (user_id, session_id))
            rows = cur.fetchall()
            cur.close()
            return rows
        except Exception as e:
            print(f"❌ DB Fetch Error: {e}")
            return []
        finally:
            if conn: conn.close()

    def delete_session(self, user_id: str, session_id: str) -> bool:
        """ลบประวัติการตรวจสอบของ Session นั้นๆ"""
        conn = None
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            
            query = "DELETE FROM initial_review_logs WHERE user_id = %s AND session_id = %s"
            cur.execute(query, (user_id, session_id))
            conn.commit()
            
            cur.close()
            return True
        except Exception as e:
            print(f"❌ DB Delete Error: {e}")
            if conn: conn.rollback()
            return False
        finally:
            if conn: conn.close()