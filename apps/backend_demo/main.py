from fastapi import FastAPI, UploadFile, File, Form, Body, HTTPException
from fastapi.responses import StreamingResponse
import io
from fastapi.middleware.cors import CORSMiddleware
from services import typhoon_service
from agents import audit_agents
from repository import AuditRepository
import shutil
import os
import uvicorn
import asyncio
import uuid

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- 1. Upload Document Endpoint (ใช้แทน save_audit เดิม) ---
@app.post("/upload_document")
async def upload_document(file: UploadFile = File(...)):
    # ... (โค้ดเดิม) ...
    try:
        file_content = await file.read()
        audit_id = str(uuid.uuid4())
        file_name = file.filename or "unknown_file"
        repo = AuditRepository()
        success = repo.save_audit_session(audit_id, file_name, file_content)
        if success:
            return {"status": "success", "audit_id": audit_id}
        raise HTTPException(status_code=500, detail="Failed DB")
    except Exception as e:
        return {"status": "error", "message": str(e)}

# --- ✅ [NEW] Endpoint ดึงชื่อไฟล์ ---
@app.get("/audit/{audit_id}/info")
def get_audit_info(audit_id: str):
    repo = AuditRepository()
    info = repo.get_audit_summary(audit_id)
    if not info:
        raise HTTPException(status_code=404, detail="Audit ID not found")
    return {"status": "success", "data": info}

# --- ✅ [NEW] Endpoint ดึงรูปภาพ/PDF ---
@app.get("/audit/{audit_id}/file")
def get_audit_file(audit_id: str):
    repo = AuditRepository()
    
    # 1. ดึงข้อมูลชื่อไฟล์ก่อนเพื่อหาประเภทไฟล์
    info = repo.get_audit_summary(audit_id)
    if not info:
         raise HTTPException(status_code=404, detail="Audit ID not found")
    
    file_name = info.get("file_name", "document.pdf")
    
    # 2. ดึงเนื้อไฟล์ Binary
    file_content = repo.get_audit_file_content(audit_id)
    if not file_content:
        raise HTTPException(status_code=404, detail="File content missing")

    # 3. กำหนด Media Type
    media_type = "application/octet-stream"
    if file_name.lower().endswith(".pdf"):
        media_type = "application/pdf"
    elif file_name.lower().endswith((".png", ".jpg", ".jpeg")):
        media_type = "image/jpeg"

    # 4. ส่งกลับเป็น Stream
    return StreamingResponse(io.BytesIO(file_content), media_type=media_type)

# --- 2. Analyze Endpoint (สำหรับวิเคราะห์ AI) ---
@app.post("/analyze")
async def analyze_document(file: UploadFile = File(...)):
    temp_path = f"temp_uploads/{file.filename}"
    
    try:
        # บันทึกไฟล์ชั่วคราวเพื่อส่งให้ OCR
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        print(f"Processing: {temp_path}")

        extracted_text = typhoon_service.extract_text(temp_path)
        print(f"Extracted {len(extracted_text)} chars. Sending to Gemini Agents...")
        
        step4_task = asyncio.to_thread(audit_agents.agent_step4_sufficiency, extracted_text)
        step6_task = asyncio.to_thread(audit_agents.agent_step6_complainant, extracted_text)
        
        step4_ai_result, step6_ai_result = await asyncio.gather(step4_task, step6_task)

        # Process Results (Logic เดิมของคุณ)
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

# --- 3. Save AI Result Endpoint ---
@app.post("/save_ai_result")
def save_ai_result(data: dict = Body(...)):
    """
    บันทึกผลลัพธ์จาก AI (รับ JSON ปกติ)
    """
    print("\n--- [API] /save_ai_result Called ---")
    audit_id = data.get("audit_id")
    step_id = data.get("step_id")
    result = data.get("result", {})

    if not audit_id or not step_id:
        return {"status": "error", "message": "Missing audit_id or step_id"}

    repo = AuditRepository()
    try:
        success = repo.save_step_log(audit_id, int(step_id), result)
        if success:
            return {"status": "success", "message": f"Step {step_id} data saved"}
        else:
            return {"status": "error", "message": "Failed to save data"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    if not os.path.exists("temp_uploads"):
        os.makedirs("temp_uploads")
    uvicorn.run(app, host="0.0.0.0", port=8000)