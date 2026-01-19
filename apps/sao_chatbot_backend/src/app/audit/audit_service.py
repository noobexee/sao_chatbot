import uuid
import io
import os
import shutil
import asyncio
import tempfile
from fastapi import UploadFile

# Correct imports based on your structure
from src.db.repositories.audit_repository import AuditRepository
from src.app.llm import audit_agents
from src.app.llm.ocr import TyphoonOCRLoader

class AuditService:
    def __init__(self):
        self.repo = AuditRepository()

    async def process_upload(self, file: UploadFile) -> dict:
        file_content = await file.read()
        audit_id = str(uuid.uuid4())
        file_name = file.filename or "unknown_file"
        
        success = self.repo.save_audit_session(audit_id, file_name, file_content)
        if success:
            return {"status": "success", "audit_id": audit_id}
        raise Exception("Database Save Failed")
    
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
            step4_task = asyncio.to_thread(audit_agents.audit_agents.agent_step4_sufficiency, extracted_text)
            step6_task = asyncio.to_thread(audit_agents.audit_agents.agent_step6_complainant, extracted_text)

            step4_ai_result, step6_ai_result = await asyncio.gather(step4_task, step6_task)

            # 5. Format Response
            step4_response = self._format_ai_response(step4_ai_result, "step4")
            step6_response = self._format_ai_response(step6_ai_result, "step6")

            return {
                "status": "success",
                "data": {
                    "step4": step4_response,
                    "step6": step6_response,
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
    
    def get_audit_info(self, audit_id: str):
        return self.repo.get_audit_summary(audit_id)

    def get_file_stream(self, audit_id: str):
        info = self.repo.get_audit_summary(audit_id)
        if not info:
             raise ValueError("Audit ID not found")
        
        file_content = self.repo.get_audit_file_content(audit_id)
        if not file_content:
            raise FileNotFoundError("File content missing")

        file_name = info.get("file_name", "doc.pdf")
        media_type = "application/pdf" if file_name.lower().endswith(".pdf") else "image/jpeg"
        
        return io.BytesIO(file_content), media_type

    def save_ai_feedback(self, audit_id, step_id, result):
        return self.repo.save_step_log(audit_id, int(step_id), result)

    def _format_ai_response(self, result: dict, step_type: str) -> dict:
        if not result:
            return {"status": "fail", "title": "AI Error", "details": {}, "people": []}
        
        if step_type == "step6":
            people_list = result.get("people", [])
            has_complainant = any(p['role'] == 'ผู้ร้องเรียน' for p in people_list)
            return {"status": "success" if has_complainant else "fail", "title": "ผู้ร้องเรียน", "people": people_list}
        
        return {
            "status": result.get("status", "fail"),
            "title": result.get("title", "การวิเคราะห์ล้มเหลว"),
            "reason": result.get("reason", "-"),
            "details": result.get("details", {})
        }