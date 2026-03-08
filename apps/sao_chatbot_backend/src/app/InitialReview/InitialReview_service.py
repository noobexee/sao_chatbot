from collections import defaultdict
import uuid
import io
import os
import shutil
import asyncio
import tempfile
from fastapi import UploadFile

from src.app.InitialReview.InitialReviewSchemas import ReviewSummary
from src.db.repositories.InitialReview_repository import InitialReviewRepository
from src.app.llm import InitialReview_agents

from src.app.llm.ocr import TyphoonOCRLoader

class InitialReviewService:
    def __init__(self):
        self.repo = InitialReviewRepository()
    
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
            extracted_text = "\n\n".join([doc.page_content for doc in documents])
            
            return extracted_text
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
        """
        วิเคราะห์เอกสารด้วย AI ครบทุกข้อพร้อมกัน (Parallel Execution)
        *หมายเหตุ: session_id จะถูกสร้างและแนบเข้ามาใน Controller*
        """
        try:
            extracted_text = await self._extract_text_from_file(file)
            print(f"Extracted {len(extracted_text)} chars. Start AI Analysis...")
            
            task_c2 = asyncio.to_thread(InitialReview_agents.InitialReview_agents.agent_criteria2_sao_authority, extracted_text)
            task_c4 = asyncio.to_thread(InitialReview_agents.InitialReview_agents.agent_criteria4_sufficiency, extracted_text)
            task_c6 = asyncio.to_thread(InitialReview_agents.InitialReview_agents.agent_criteria6_complainant, extracted_text)
            task_c8 = asyncio.to_thread(InitialReview_agents.InitialReview_agents.agent_criteria8_other_authority, extracted_text)

            res_c2, res_c4, res_c6, res_c8 = await asyncio.gather(task_c2, task_c4, task_c6, task_c8)

            return {
                "status": "success",
                "data": {
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
        """ส่งข้อมูลไปบันทึกลง Database ผ่าน Repository"""
        return self.repo.save_criteria_log(user_id, session_id, criteria_id, ai_result, feedback)

    def get_all_sessions(self, user_id: str):
        """ดึงประวัติ Session ทั้งหมดของ User"""
        return self.repo.get_all_sessions(user_id)

    def get_review_by_session(self, user_id: str, session_id: str):
        """ดึงรายละเอียดการตรวจของ 1 Session"""
        return self.repo.get_review_by_session(user_id, session_id)

    def delete_session(self, user_id: str, session_id: str) -> bool:
        """ลบประวัติการตรวจสอบ"""
        return self.repo.delete_session(user_id, session_id)

    def _format_ai_response(self, result: dict, criteria_type: str) -> dict:
        """จัด Format สำหรับ Criteria ทั่วไป (ข้อ 4 และ 6)"""
        if not result:
            return {"status": "fail", "title": "AI Error", "details": {}, "people": []}
        
        if criteria_type == "criteria6":
            people_list = result.get("people", [])
            has_complainant = any(p.get('role', '') == 'ผู้ร้องเรียน' for p in people_list)
            return {
                "status": "success" if has_complainant else "fail", 
                "title": "ผู้ร้องเรียน", 
                "people": people_list
            }
        
        return result

    def _format_authority_response(self, result: dict, criteria_id: int) -> dict:
        """จัด Format สำหรับ Criteria 2 และ 8 (รองรับระบบ HITL)"""
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

    def get_InitialReview_file_content(self, InitialReview_id: str):
        info = self.repo.get_InitialReview_summary(InitialReview_id)
        if not info:
             raise ValueError("InitialReview ID not found")
        
        file_content = self.repo.get_InitialReview_file_content(InitialReview_id)
        if not file_content:
            raise FileNotFoundError("File content missing")

        file_name = info.get("file_name", "doc.pdf")
        media_type = "application/pdf" if file_name.lower().endswith(".pdf") else "image/jpeg"
        
        return io.BytesIO(file_content), media_type
    
    def get_InitialReview_summary(self, user_id: str, InitialReview_id: str):
        rows = self.repo.get_review_by_session(
            user_id=user_id,
            session_id=InitialReview_id
        )

        if not rows:
            return None

        criteria_map = defaultdict(dict)

        for r in rows:
            criteria_id = r[0]
            field_type = r[1]
            criteria_map[criteria_id][field_type] = r

        def pick(row):
            return row[4] if row[5] else row[2]

        summary = ReviewSummary()

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
                value = row[4]  # always user_value

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
                entity is not None,
                behavior is not None,
                official is not None,
                (date is not None and location is not None)
            ]

        # -------- Criteria 5 --------
        if 5 in criteria_map:
            row = criteria_map[5].get("raw_result")

            if row:
                value = row[4]  # always user_value
                summary.criteria_5 = (value == "ไม่เคยแจ้ง")

        # -------- Criteria 6 --------
        if 6 in criteria_map:
            row = criteria_map[6].get("people_list")

            if row:
                # we only check existence for now
                people = pick(row)

                summary.criteria_6 = [
                    None,           # complainant can be null
                    bool(people),   # accused exists
                    bool(people)    # witness exists
                ]

        # -------- Criteria 7 --------
        if 7 in criteria_map:
            row = criteria_map[7].get("raw_result")

            if row:
                value = row[4]  # always user_value

                if value == "เป็น":
                    summary.criteria_7 = {True: "พบหน่วยงานที่เกี่ยวข้อง"}
                else:
                    summary.criteria_7 = {False: None}

        # -------- Criteria 8 --------
        if 8 in criteria_map:
            result_row = criteria_map[8].get("criteria8_result")
            reason_row = criteria_map[8].get("criteria8_reason")

            if result_row:
                result = pick(result_row) == "เป็น"
                reason = pick(reason_row) if reason_row else ""

                summary.criteria_8 = {result: reason}
        print(summary)
        return summary

        