import uuid
import io
import os
import shutil
import asyncio
import tempfile
from fastapi import UploadFile

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