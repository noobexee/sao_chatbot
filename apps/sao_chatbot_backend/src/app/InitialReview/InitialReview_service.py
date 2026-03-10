from collections import defaultdict
import os
import re
import shutil
import asyncio
import tempfile
from fastapi import UploadFile
import json

from src.app.InitialReview.InitialReviewSchemas import ReviewSummary
from src.db.repositories.InitialReview_repository import InitialReviewRepository
from src.app.llm import InitialReview_agents
from src.app.InitialReview.InitialReview_matcher import agency_matcher


from src.app.llm.ocr import TyphoonOCRLoader


class InitialReviewService:
    def __init__(self):
        self.repo = InitialReviewRepository()
        self.OCR_CORRECTIONS = {
            r"โรงพยาบาลบ้านหลวงพ่อ เป็น": "โรวพยาบาลบ้านหลวงพ่อเปิ่น",
            r"หลวงพ่อ เป็น": "หลวงพ่อเปิ่น",
            r"โรงเรียนบ้านหนอง ใหญ่": "โรงเรียนบ้านหนองใหญ่",
            r"เทศบาลตำบล หนอง": "เทศบาลตำบลหนอง",
            r"องค์การบริหารส่วน ตำบล": "องค์การบริหารส่วนตำบล",
            r"สถาบันวิจัยและพัฒนา วิทยาศาสตร์และเทคโนโลยี มช.": "สถาบันวิจัยและพัฒนาวิทยาศาสตร์และเทคโนโลยีมช"
        }

    def _fix_ocr_typos(self, text: str) -> str:
        if not text:
            return ""
        fixed_text = text
        for wrong_pattern, correct_word in self.OCR_CORRECTIONS.items():
            fixed_text = re.sub(wrong_pattern, correct_word, fixed_text, flags=re.IGNORECASE)
        return fixed_text

    async def _extract_text_from_file(self, file: UploadFile) -> str:
        temp_path = None
        try:
            suffix = os.path.splitext(file.filename or "")[1]
            if not suffix:
                suffix = ".tmp"

            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                shutil.copyfileobj(file.file, tmp)
                temp_path = tmp.name

            loader = TyphoonOCRLoader(file_path=temp_path)
            documents = loader.load()
            raw_text = "\n\n".join([doc.page_content for doc in documents])

            cleaned_text = self._fix_ocr_typos(raw_text)

            return cleaned_text
        finally:
            if temp_path and os.path.exists(temp_path):
                os.remove(temp_path)

    async def ocr_document_logic(self, file: UploadFile) -> dict:
        try:
            extracted_text = await self._extract_text_from_file(file)
            return {"status": "success", "text": extracted_text}
        except Exception as e:
            print(f"OCR Error: {e}")
            raise e

    async def analyze_document_logic(self, file: UploadFile) -> dict:
        try:
            extracted_text = await self._extract_text_from_file(file)
            print(f"Extracted {len(extracted_text)} chars. Start AI Analysis...")

            task_c2 = asyncio.to_thread(
                InitialReview_agents.InitialReview_agents.agent_criteria2_sao_authority,
                extracted_text
            )
            task_c4 = asyncio.to_thread(
                InitialReview_agents.InitialReview_agents.agent_criteria4_sufficiency,
                extracted_text
            )
            task_c6 = asyncio.to_thread(
                InitialReview_agents.InitialReview_agents.agent_criteria6_complainant,
                extracted_text
            )
            task_c8 = asyncio.to_thread(
                InitialReview_agents.InitialReview_agents.agent_criteria8_other_authority,
                extracted_text
            )

            res_c2, res_c4, res_c6, res_c8 = await asyncio.gather(
                task_c2, task_c4, task_c6, task_c8
            )

            res_c1 = {
                "status": "fail",
                "title": "หน่วยรับตรวจ",
                "data": None,
                "reason": "ไม่พบข้อมูลหน่วยรับตรวจ",
                "match_type": "None"
            }

            extracted_entity = None
            if res_c4 and "details" in res_c4 and "entity" in res_c4["details"]:
                entity_field = res_c4["details"]["entity"]
                if isinstance(entity_field, dict):
                    extracted_entity = entity_field.get("value")
                else:
                    extracted_entity = entity_field

            if extracted_entity and getattr(agency_matcher, "is_ready", False):
                matcher_result = agency_matcher.search_agency(extracted_entity)

                if matcher_result.get("status") == "pending_llm":
                    candidates = matcher_result.get("candidates", [])
                    print(
                        f"🔍 C1 LLM Judge Triggered! Entity: '{extracted_entity}', Candidates (search_keys): {candidates}"
                    )

                    judge_res = await asyncio.to_thread(
                        InitialReview_agents.InitialReview_agents.agent_criteria1_judge,
                        extracted_entity,
                        candidates,
                        extracted_text
                    )

                    if judge_res and judge_res.get("selected_candidate") != "Not Found":
                        selected_search_key = judge_res.get("selected_candidate")

                        db_result = agency_matcher.get_agency_by_search_key(
                            selected_search_key
                        )

                        if db_result["status"] == "success":
                            res_c1 = db_result
                            res_c1["reason"] = judge_res.get("reason", "ตัดสินโดย LLM")
                        else:
                            res_c1["status"] = "fail"
                            res_c1["match_type"] = "Not Found"
                            res_c1["reason"] = "AI เลือกว่าตรง แต่ไม่พบข้อมูลในฐานข้อมูล"
                    else:
                        res_c1["status"] = "fail"
                        res_c1["match_type"] = "Not Found"
                        res_c1["reason"] = judge_res.get(
                            "reason", "AI วิเคราะห์แล้วไม่ตรงกับฐานข้อมูล"
                        )
                else:
                    res_c1 = matcher_result

            return {
                "status": "success",
                "data": {
                    "criteria1": res_c1,
                    "criteria2": self._format_authority_response(res_c2, 2),
                    "criteria4": self._format_ai_response(res_c4, "criteria4"),
                    "criteria6": self._format_ai_response(res_c6, "criteria6"),
                    "criteria8": self._format_authority_response(res_c8, 8),
                    "raw_text": extracted_text[:200]
                }
            }

        except Exception as e:
            print(f"Analyze Error: {e}")
            raise e

    def save_criteria_log(self, user_id: str, session_id: str, criteria_id: int, ai_result: dict, feedback: str = None) -> bool:
        return self.repo.save_criteria_log(user_id, session_id, criteria_id, ai_result, feedback)

    def get_user_sessions(self, user_id: str):
        return self.repo.get_user_sessions(user_id)

    def get_review_by_session(self, user_id: str, session_id: str):
        return self.repo.get_review_by_session(user_id, session_id)

    def delete_session(self, user_id: str, session_id: str) -> bool:
        return self.repo.delete_session(user_id, session_id)

    def _format_ai_response(self, result: dict, criteria_type: str) -> dict:
        if not result:
            return {"status": "fail", "title": "AI Error", "details": {}, "people": []}

        if criteria_type == "criteria6":
            people_list = result.get("people", [])
            has_complainant = any(p.get("role", "") == "ผู้ร้องเรียน" for p in people_list)
            return {
                "status": "success" if has_complainant else "fail",
                "title": "ผู้ร้องเรียน",
                "people": people_list
            }

        return result

    def _format_authority_response(self, result: dict, criteria_id: int) -> dict:
        if not result:
            return {"status": "fail", "title": "AI Error", "result": "-", "reason": "AI Error"}

        title = "อำนาจหน้าที่ สตง." if criteria_id == 2 else "อำนาจองค์กรอิสระอื่น"
        return {
            "status": result.get("status", "neutral"),
            "title": title,
            "result": result.get("result", "-"),
            "reason": result.get("reason", "-"),
            "evidence": result.get("evidence", "-"),
            "organization": result.get("organization", None)
        }

    def get_InitialReview_summary(self, user_id: str, InitialReview_id: str):
        rows = self.repo.get_review_by_session(
            user_id=user_id,
            session_id=InitialReview_id
        )

        if not rows:
            return None

        criteria_map = defaultdict(dict)

        for r in rows:
            print(r)
            criteria_id = r[0]
            field_type = r[1]
            criteria_map[criteria_id][field_type] = r

        def pick(row):
            return row[2] if row[5] else row[4]

        def has_text(value):
            return value is not None and str(value).strip() != ""

        summary = ReviewSummary()

        # -------- OCR (Criteria 0) --------
        if 0 in criteria_map:
            row = criteria_map[0].get("ocr_text")
            if row:
                ocr_text = pick(row)
                summary.OCR_text = ocr_text

        # -------- Criteria 1 --------
        if 1 in criteria_map:
            result_row = criteria_map[1].get("raw_result")
            print(f"Criteria 1 Row: {result_row}")

            if result_row:
                value = pick(result_row)
                summary.criteria_1 = (value == "เป็น")

        # -------- Criteria 2 --------
        if 2 in criteria_map:
            result_row = criteria_map[2].get("criteria2_result")

            if result_row:
                value = pick(result_row)
                summary.criteria_2 = (value == "เป็น")

        # -------- Criteria 3 --------
        if 3 in criteria_map:
            row = criteria_map[3].get("raw_result")

            if row:
                value = row[4]

                if value == "ไม่เกิน":
                    summary.criteria_3 = True
                elif value == "เกิน":
                    summary.criteria_3 = False
                else:
                    summary.criteria_3 = None

        # -------- Criteria 4 --------
        if 4 in criteria_map:
            c4 = criteria_map[4]

            entity = pick(c4["entity"]) if "entity" in c4 else None
            behavior = pick(c4["behavior"]) if "behavior" in c4 else None
            official = pick(c4["official"]) if "official" in c4 else None
            date = pick(c4["date"]) if "date" in c4 else None
            location = pick(c4["location"]) if "location" in c4 else None

            summary.criteria_4 = [
                has_text(entity),
                has_text(behavior),
                has_text(official),
                has_text(date) and has_text(location)
            ]

        # -------- Criteria 5 --------
        if 5 in criteria_map:
            row = criteria_map[5].get("raw_result")

            if row:
                value = row[4]
                summary.criteria_5 = (value == "ไม่เคยแจ้ง")

        # -------- Criteria 6 --------
        if 6 in criteria_map:
            row = criteria_map[6].get("people_list")

            if row:
                people_raw = pick(row)
                try:
                    people = json.loads(people_raw) if has_text(people_raw) else []
                except Exception as e:
                    print("JSON error:", e)
                    people = []

                has_complainant = any(p.get("role") == "ผู้ร้องเรียน" for p in people)
                has_accused = any(p.get("role") == "ผู้ถูกร้องเรียน" for p in people)
                has_witness = any(p.get("role") == "พยาน" for p in people)

                summary.criteria_6 = [
                    bool(has_complainant),
                    bool(has_accused),
                    bool(has_witness)
                ]

        # -------- Criteria 7 --------
        if 7 in criteria_map:
            row = criteria_map[7].get("raw_result")

            if row:
                value = row[4]

                if value == "เป็น":
                    summary.criteria_7 = {False: None}
                else:
                    summary.criteria_7 = {True: "พบหน่วยงานที่เกี่ยวข้อง"}

        # -------- Criteria 8 --------
        if 8 in criteria_map:
            result_row = criteria_map[8].get("criteria8_result")
            reason_row = criteria_map[8].get("criteria8_reason")

            if result_row:
                result = pick(result_row) == "เป็น"
                reason = pick(reason_row) if reason_row else ""

                summary.criteria_8 = {result: reason}

        return summary
    

initial_review = InitialReviewService()