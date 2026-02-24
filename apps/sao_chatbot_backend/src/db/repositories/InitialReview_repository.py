import json
from src.db.connection import get_db_connection

class InitialReviewRepository:
    
    def save_criteria_log(self, review_id: str, criteria_id: int, ai_result: dict, feedback: str = None) -> bool:
        """
        บันทึก Log ผลการตรวจสอบรายข้อ (Criteria) เพื่อนำไปพัฒนา AI
        รองรับ Criteria 2, 4, 6, 8 และตัดระบบ Session เก่าออกแล้ว
        """
        print(f"   [DB] Saving Log: ReviewID={review_id}, Criteria={criteria_id}, Feedback={feedback}")
        conn = None
        try:
            conn = get_db_connection()
            cur = conn.cursor()

            # Note: สมมติว่าตารางใน DB ยังใช้ชื่อคอลัมน์ InitialReview_id อยู่
            # เราจะ map review_id (จาก memory) ลงไปใน column นั้น
            query_log = """
                INSERT INTO InitialReview_feedback_logs 
                (InitialReview_id, criteria_id, field_type, ai_value, user_edit, user_value, result_correct, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
            """

            # --- Logic คำนวณความถูกต้อง (Result Correctness) ---
            # ถ้า user กด dislike (down) ถือว่า AI ผิด (False)
            default_correctness = False if feedback == 'down' else True

            # =========================================================
            # ✅ Criteria 2: อำนาจหน้าที่ สตง. (SAO Authority)
            # =========================================================
            if criteria_id == 2:
                # ดึงข้อมูลจาก authority object (ถ้าไม่มีให้หาจาก root)
                authority_data = ai_result.get('authority', ai_result)
                
                # Field ที่ต้องการเก็บ
                fields = ['result', 'reason', 'evidence']
                
                for field in fields:
                    val = authority_data.get(field, "-")
                    cur.execute(query_log, (
                        review_id,
                        2,              # criteria_id
                        f"c2_{field}",  # field_type เช่น c2_result, c2_reason
                        str(val),       # ai_value
                        False, "",      # user_edit (ยังไม่มี UI แก้ไขสำหรับข้อนี้)
                        default_correctness
                    ))

            # =========================================================
            # ✅ Criteria 8: อำนาจองค์กรอิสระอื่น (Other Authority)
            # =========================================================
            elif criteria_id == 8:
                authority_data = ai_result.get('authority', ai_result)
                
                # มี organization เพิ่มเข้ามา
                fields = ['result', 'organization', 'reason', 'evidence']
                
                for field in fields:
                    val = authority_data.get(field, "-")
                    cur.execute(query_log, (
                        review_id,
                        8,              # criteria_id
                        f"c8_{field}",  # field_type
                        str(val),       # ai_value
                        False, "",
                        default_correctness
                    ))

            # =========================================================
            # ✅ Criteria 4: ความครบถ้วน (Sufficiency)
            # =========================================================
            elif criteria_id == 4:
                details = ai_result.get('details', {})
                if not isinstance(details, dict): details = {}

                for key, item in details.items():
                    # รองรับ Structured Data {original:..., value:..., isEdited:...}
                    if isinstance(item, dict) and 'original' in item:
                        ai_val = str(item.get('original', ""))
                        is_edited = bool(item.get('isEdited', False))
                        user_val = str(item.get('value', "")) if is_edited else ""
                        
                        # ถ้ามีการแก้ไข แสดงว่า AI ผิด
                        result_correct = False if is_edited else default_correctness

                        cur.execute(query_log, (
                            review_id, 4, key, ai_val, is_edited, user_val, result_correct
                        ))
                    else:
                        # Fallback (Simple string)
                        cur.execute(query_log, (
                            review_id, 4, key, str(item), False, "", default_correctness
                        ))

            # =========================================================
            # ✅ Criteria 6: ผู้ร้องเรียน (Complainant)
            # =========================================================
            elif criteria_id == 6:
                people = ai_result.get('people', [])
                ai_value_str = json.dumps(people, ensure_ascii=False)

                cur.execute(query_log, (
                    review_id,
                    6,
                    "people_list",
                    ai_value_str,
                    False, "",
                    default_correctness
                ))

            # =========================================================
            # ⚪ Default / Other Criteria (Manual or Unknown)
            # =========================================================
            else:
                # เก็บ Raw JSON ไปเลย
                cur.execute(query_log, (
                    review_id,
                    criteria_id,
                    "raw_result",
                    json.dumps(ai_result, ensure_ascii=False),
                    False, "", 
                    default_correctness
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