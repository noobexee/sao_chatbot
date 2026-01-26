import uuid
import io
import os
import shutil
import asyncio
import tempfile
from fastapi import UploadFile

# Correct imports based on your structure
from src.db.repositories.InitialReview_repository import InitialReviewRepository
from src.app.llm import InitialReview_agents
from src.app.llm.ocr import TyphoonOCRLoader

class InitialReviewService:
    def __init__(self):
        self.repo = InitialReviewRepository()
    
    async def analyze_document_logic(self, file: UploadFile) -> dict:
        temp_path = None
        try:
            # 1. Define suffix FIRST
            # We get the file extension (e.g., ".pdf") to ensure temp file has correct type
            suffix = os.path.splitext(file.filename or "")[1]
            if not suffix:
                suffix = ".tmp" # Fallback if no extension

            # 2. Use suffix in NamedTemporaryFile
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                shutil.copyfileobj(file.file, tmp)
                temp_path = tmp.name

            # 3. Process with OCR
            loader = TyphoonOCRLoader(file_path=temp_path)
            
            # สั่ง Load เอกสาร
            documents = loader.load()
            
            # รวมข้อความจากทุกหน้าเข้าด้วยกัน
            extracted_text = "\n\n".join([doc.page_content for doc in documents])
            print(f"Extracted {len(extracted_text)} chars. Sending to Gemini Agents...")
            
            # 4. AI Agents
            criteria4_task = asyncio.to_thread(InitialReview_agents.InitialReview_agents.agent_criteria4_sufficiency, extracted_text)
            criteria6_task = asyncio.to_thread(InitialReview_agents.InitialReview_agents.agent_criteria6_complainant, extracted_text)

            criteria4_ai_result, criteria6_ai_result = await asyncio.gather(criteria4_task, criteria6_task)

            # 5. Format Response
            criteria4_response = self._format_ai_response(criteria4_ai_result, "criteria4")
            criteria6_response = self._format_ai_response(criteria6_ai_result, "criteria6")

            return {
                "status": "success",
                "data": {
                    "criteria4": criteria4_response,
                    "criteria6": criteria6_response,
                    "raw_text": extracted_text[:200]
                }
            }
        except Exception as e:
            print(f"Error in analyze_document_logic: {e}")
            raise e
        finally:
            # Cleanup temp file
            if temp_path and os.path.exists(temp_path):
                os.remove(temp_path)

    def get_file_stream(self, InitialReview_id: str):
        info = self.repo.get_InitialReview_summary(InitialReview_id)
        if not info:
             raise ValueError("InitialReview ID not found")
        
        file_content = self.repo.get_InitialReview_file_content(InitialReview_id)
        if not file_content:
            raise FileNotFoundError("File content missing")

        file_name = info.get("file_name", "doc.pdf")
        media_type = "application/pdf" if file_name.lower().endswith(".pdf") else "image/jpeg"
        
        return io.BytesIO(file_content), media_type

    def save_ai_feedback(self, InitialReview_id, criteria_id, result):
        return self.repo.save_criteria_log(InitialReview_id, int(criteria_id), result)

    def _format_ai_response(self, result: dict, criteria_type: str) -> dict:
        if not result:
            return {"status": "fail", "title": "AI Error", "details": {}, "people": []}
        
        if criteria_type == "criteria6":
            people_list = result.get("people", [])
            has_complainant = any(p['role'] == 'ผู้ร้องเรียน' for p in people_list)
            return {"status": "success" if has_complainant else "fail", "title": "ผู้ร้องเรียน", "people": people_list}
        
        return {
            "status": result.get("status", "fail"),
            "title": result.get("title", "การวิเคราะห์ล้มเหลว"),
            "reason": result.get("reason", "-"),
            "details": result.get("details", {})
        }