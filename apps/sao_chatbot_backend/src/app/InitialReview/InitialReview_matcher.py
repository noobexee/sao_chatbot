import re
from typing import Dict, Any, List, Optional
from contextlib import closing
from src.db.connection import get_db_connection


class AgencyMatcher:
    FUZZY_THRESHOLD = 0.6
    STRONG_MATCH_THRESHOLD = 0.8
    MAX_CANDIDATES = 3

    THAI_ABBREVIATIONS = {
        "รพ.สต.": "โรงพยาบาลส่งเสริมสุขภาพตำบล",
        "ร.ร.": "โรงเรียน",
        "รพ.": "โรงพยาบาล",
        "อบต.": "องค์การบริหารส่วนตำบล",
        "อบจ.": "องค์การบริหารส่วนจังหวัด",
        "ทต.": "เทศบาลตำบล",
        "ทม.": "เทศบาลเมือง",
        "ทน.": "เทศบาลนคร",
        "จ.": "จังหวัด",
        "อ.": "อำเภอ",
        "ต.": "ตำบล",
    }

    def __init__(self):
        self.is_ready = True

    # ================= NORMALIZE =================

    def _normalize_text(self, text: Optional[str]) -> str:
        if not text:
            return ""

        text = str(text).strip()
        text = text.replace(" ", "").replace("\u200b", "")

        # longest abbrev first (prevent partial replace bug)
        for short in sorted(self.THAI_ABBREVIATIONS, key=len, reverse=True):
            text = text.replace(short, self.THAI_ABBREVIATIONS[short])

        text = re.sub(r'[^ก-๙a-zA-Z0-9]', '', text)

        return text.lower()

    # ================= PUBLIC SEARCH =================

    def search_agency(self, extracted_entity: str) -> Dict[str, Any]:
        if not extracted_entity:
            return self._fail("ไม่พบข้อมูลชื่อหน่วยรับตรวจจากเอกสาร")

        query_key = self._normalize_text(extracted_entity)

        if len(query_key) < 3:
            return self._fail("ชื่อหน่วยรับตรวจสั้นเกินไป")

        try:
            with closing(get_db_connection()) as conn, closing(conn.cursor()) as cur:

                # ---------- Exact Match ----------
                cur.execute(
                    """
                    SELECT agency_name, department_name, ministry_name
                    FROM initial_review_agencies
                    WHERE search_key = %s
                    """,
                    (query_key,),
                )

                rows = cur.fetchall()
                if rows:
                    return self._success(rows, "Exact Match")

                # ---------- Fuzzy Match ----------
                cur.execute(
                    """
                    SELECT agency_name,
                           department_name,
                           ministry_name,
                           search_key,
                           similarity(search_key, %s) AS score
                    FROM initial_review_agencies
                    WHERE similarity(search_key, %s) > %s
                    ORDER BY score DESC
                    LIMIT 5
                    """,
                    (query_key, query_key, self.FUZZY_THRESHOLD),
                )

                fuzzy_rows = cur.fetchall()

                if not fuzzy_rows:
                    return self._fail("ไม่พบข้อมูลที่ใกล้เคียงในฐานข้อมูล")

                best_score = fuzzy_rows[0][4]

                # ---------- Strong fuzzy → auto accept ----------
                if best_score >= self.STRONG_MATCH_THRESHOLD:
                    return self._success(
                        [(r[0], r[1], r[2]) for r in fuzzy_rows],
                        f"Fuzzy Match ({best_score*100:.1f}%)"
                    )

                # ---------- Weak fuzzy → send candidates to LLM ----------
                candidates = list(
                    dict.fromkeys([r[3] for r in fuzzy_rows])
                )[: self.MAX_CANDIDATES]

                return {
                    "status": "pending_llm",
                    "extracted_name": extracted_entity,
                    "candidates": candidates,
                }

        except Exception as e:
            print(f"❌ AgencyMatcher Error: {e}")
            return self._fail("ระบบฐานข้อมูลขัดข้อง")

    # ================= LLM PICK FETCH =================

    def get_agency_by_search_key(self, search_key: str) -> Dict[str, Any]:
        try:
            with closing(get_db_connection()) as conn, closing(conn.cursor()) as cur:

                cur.execute(
                    """
                    SELECT agency_name, department_name, ministry_name
                    FROM initial_review_agencies
                    WHERE search_key = %s
                    """,
                    (search_key,),
                )

                rows = cur.fetchall()

                if not rows:
                    return self._fail("ไม่พบข้อมูลที่ LLM เลือกในฐานข้อมูล")

                return self._success(rows, "LLM Judge")

        except Exception as e:
            print(f"❌ DB Fetch Error: {e}")
            return self._fail("ระบบฐานข้อมูลขัดข้อง")

    # ================= FORMAT =================

    def _success(self, rows: List[tuple], match_type: str) -> Dict[str, Any]:
        agency_name = rows[0][0]

        hierarchies = []
        seen = set()

        for agency, dept, ministry in rows:
            key = (dept, ministry)
            if key in seen:
                continue
            seen.add(key)

            hierarchies.append({
                "department": dept or "-",
                "ministry": ministry or "-"
            })

        return {
            "status": "success",
            "match_type": match_type,
            "data": {
                "agency_name": agency_name,
                "match_count": len(hierarchies),
                "hierarchies": hierarchies,
            },
        }

    def _fail(self, reason: str) -> Dict[str, Any]:
        return {
            "status": "fail",
            "match_type": "Not Found",
            "data": None,
            "reason": reason,
        }


agency_matcher = AgencyMatcher()