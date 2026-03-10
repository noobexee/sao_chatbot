import re
from typing import Dict, Any, List
from src.db.connection import get_db_connection

class AgencyMatcher:
    def __init__(self):
        self.is_ready = True 
        
        self.THAI_ABBREVIATIONS = {
            "ร.ร.": "โรงเรียน", "รพ.": "โรงพยาบาล", "รพ.สต.": "โรงพยาบาลส่งเสริมสุขภาพตำบล",
            "อบต.": "องค์การบริหารส่วนตำบล", "ทต.": "เทศบาลตำบล", "อบจ.": "องค์การบริหารส่วนจังหวัด",
            "ทม.": "เทศบาลเมือง", "ทน.": "เทศบาลนคร", "จ.": "จังหวัด", "อ.": "อำเภอ", "ต.": "ตำบล"
        }

    def _normalize_text(self, text: str) -> str:
        if not text: return ""
        text = str(text).strip() 
        text = text.replace(" ", "").replace("\u200b", "") 

        for short, full in self.THAI_ABBREVIATIONS.items(): #✅ cover most of the case in db 
            text = text.replace(short, full) 

        text = re.sub(r'[^ก-๙a-zA-Z0-9]', '', text) #✅ replace all non-alphanumeric Thai/English characters (including punctuation) with empty string
        
        return text.lower()

    def search_agency(self, extracted_entity: str) -> Dict[str, Any]:
        if not extracted_entity:
            return self._build_not_found_response("ไม่พบข้อมูลชื่อหน่วยรับตรวจจากเอกสาร")

        query_key = self._normalize_text(extracted_entity)
        if len(query_key) < 3:
            return self._build_not_found_response("ชื่อหน่วยรับตรวจสั้นเกินไป")

        conn = None
        try:
            conn = get_db_connection()
            cur = conn.cursor()

            # 🌊 ด่าน 1: Exact Match (เปรียบเทียบ search_key)
            cur.execute("""
                SELECT agency_name, agency_code, department_name, ministry_name, department_code, ministry_code
                FROM initial_review_agencies 
                WHERE search_key = %s
            """, (query_key,))
            
            matches = cur.fetchall()
            if matches:
                return self._format_result(matches, "Exact Match")

            # 🌊 ด่าน 2: Fuzzy Match (ดึง search_key ออกมาใน index ที่ 7)
            cur.execute("""
                SELECT agency_name, agency_code, department_name, ministry_name, department_code, ministry_code,
                       similarity(search_key, %s) as score, search_key
                FROM initial_review_agencies 
                WHERE similarity(search_key, %s) > 0.6
                ORDER BY score DESC 
                LIMIT 5
            """, (query_key, query_key))
            
            fuzzy_results = cur.fetchall()
            
            if fuzzy_results:
                best_score = fuzzy_results[0][6] # คะแนน Score
                
                if best_score >= 0.8:
                    best_search_key = fuzzy_results[0][7] # ดึง search_key
                    cur.execute("""
                        SELECT agency_name, agency_code, department_name, ministry_name, department_code, ministry_code
                        FROM initial_review_agencies 
                        WHERE search_key = %s
                    """, (best_search_key,))
                    return self._format_result(cur.fetchall(), f"Fuzzy Match ({best_score*100:.1f}%)")
                
                # 🟢 คลุมเครือ ส่งต่อให้ LLM Judge โดยส่ง "search_key" (row[7]) เป็น Candidate
                candidates = list(dict.fromkeys([row[7] for row in fuzzy_results]))[:3]
                return {
                    "status": "pending_llm",
                    "extracted_name": extracted_entity,
                    "candidates": candidates
                }

            return self._build_not_found_response("ไม่พบข้อมูลที่ใกล้เคียงในฐานข้อมูล")

        except Exception as e:
            print(f"❌ AgencyMatcher DB Error: {e}")
            return self._build_not_found_response("ระบบฐานข้อมูลขัดข้อง")
        finally:
            if conn:
                cur.close()
                conn.close()

    # 🟢 NEW: ฟังก์ชันสำหรับค้นหาด้วย search_key จากตัวเลือกที่ LLM คืนมา
    def get_agency_by_search_key(self, search_key: str) -> Dict[str, Any]:
        """ดึงข้อมูลทั้งหมดของหน่วยงานจาก search_key ที่ LLM เลือก (ใช้ในด่าน LLM Judge)"""
        conn = None
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute("""
                SELECT agency_name, agency_code, department_name, ministry_name, department_code, ministry_code
                FROM initial_review_agencies 
                WHERE search_key = %s
            """, (search_key,))
            
            matches = cur.fetchall()
            if matches:
                return self._format_result(matches, "LLM Judge")
            return self._build_not_found_response("ไม่พบข้อมูลที่ LLM เลือกในฐานข้อมูล")
            
        except Exception as e:
            print(f"❌ DB Fetch Error in get_agency_by_search_key: {e}")
            return self._build_not_found_response("ระบบฐานข้อมูลขัดข้อง")
        finally:
            if conn:
                cur.close()
                conn.close()

    def _format_result(self, rows: List[tuple], match_type: str) -> Dict:
        agency_name = rows[0][0]
        hierarchies = []
        seen = set()
        
        for r in rows:
            h_key = f"{str(r[1])}_{str(r[4])}"
            if h_key not in seen:
                seen.add(h_key)
                hierarchies.append({
                    "agency_id": str(r[1]) if r[1] else "-",
                    "department": str(r[2]) if r[2] else "-",
                    "ministry": str(r[3]) if r[3] else "-",
                    "department_id": str(r[4]) if len(r) > 4 and r[4] else "-",
                    "ministry_id": str(r[5]) if len(r) > 5 and r[5] else "-"
                })
            
        return {
            "status": "success",
            "match_type": match_type,
            "data": {
                "agency_name": agency_name,
                "match_count": len(hierarchies),
                "hierarchies": hierarchies
            }
        }
        
    def _build_not_found_response(self, reason: str) -> Dict:
        return {"status": "fail", "match_type": "Not Found", "data": None, "reason": reason}

agency_matcher = AgencyMatcher()