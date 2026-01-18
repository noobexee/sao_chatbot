import io
from apps.sao_chatbot_backend.src.app.chatbot.retriever import Retriever
from fastapi import APIRouter, Body, UploadFile, File
import uuid
import asyncio
from apps.sao_chatbot_backend.src.app.audit.audit_service import AuditRepository
from apps.sao_chatbot_backend.src.app.llm import audit_agents
import shutil
import os
from src.app.llm.ocr import TyphoonOCRLoader

class AuditService:
    def __init__(self):
        self.repo = AuditRepository()

    async def process_upload(self, file) -> dict:
        file_content = await file.read()
        audit_id = str(uuid.uuid4())
        file_name = file.filename or "unknown_file"
        
        success = self.repo.save_audit_session(audit_id, file_name, file_content)
        if success:
            return {"status": "success", "audit_id": audit_id}
        raise Exception("Database Save Failed")
    
    async def analyze_document_logic(self, file) -> dict:
        # สร้างโฟลเดอร์ชั่วคราวถ้ายังไม่มี
        if not os.path.exists("temp_uploads"):
            os.makedirs("temp_uploads")
            
        temp_path = f"temp_uploads/{file.filename}"
        
        try:
            # 1. Save Temp File
            with open(temp_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            
            # 2. OCR Service
            extracted_text = TyphoonOCRLoader.extract_text_only(temp_path)
            
            # 3. AI Agents (Parallel Execution)
            step4_task = asyncio.to_thread(audit_agents.agent_step4_sufficiency, extracted_text)
            step6_task = asyncio.to_thread(audit_agents.agent_step6_complainant, extracted_text)
            
            step4_ai_result, step6_ai_result = await asyncio.gather(step4_task, step6_task)

            # Process Results
            if step4_ai_result:
                step4_response = {
                    "status": step4_ai_result.get("status", "fail"),
                    "title": step4_ai_result.get("title", "การวิเคราะห์ล้มเหลว"),
                    "reason": step4_ai_result.get("reason", "-"),
                    "details": step4_ai_result.get("details", {})
                }
            else:
                step4_response = {"status": "fail", "title": "AI Error", "details": {}}

            if step6_ai_result:
                people_list = step6_ai_result.get("people", [])
                has_complainant = any(p['role'] == 'ผู้ร้องเรียน' for p in people_list)
                
                step6_response = {
                    "status": "success" if has_complainant else "fail",
                    "title": "รายละเอียดของผู้ร้องเรียน",
                    "people": people_list
                }
            else:
                step6_response = {"status": "fail", "title": "AI Error", "people": []}

            if os.path.exists(temp_path):
                os.remove(temp_path)

            return {
                "status": "success",
                "data": {
                    "step4": step4_response,
                    "step6": step6_response,
                    "raw_text": extracted_text[:200]
                }
            }

        except Exception as e:
            print(f"Error: {e}")
            if os.path.exists(temp_path):
                os.remove(temp_path)
            return {"status": "error", "message": str(e)}    
    
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
