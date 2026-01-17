from fastapi import FastAPI, UploadFile, File, Body
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

# --- Analyze Endpoint (Async) ---
@app.post("/analyze")
async def analyze_document(file: UploadFile = File(...)):
    temp_path = f"temp_uploads/{file.filename}"
    
    try:
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        print(f"Processing: {temp_path}")

        extracted_text = typhoon_service.extract_text(temp_path)
        print(f"Extracted {len(extracted_text)} chars. Sending to Gemini Agents...")
        
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

# --- Save Session Endpoint (Auto UUID) ---
@app.post("/save_audit")
def save_audit(data: dict = Body(...)):
    """
    Saves only the audit session.
    - If 'audit_id' is NOT provided, it generates a new UUID.
    - Returns 'audit_id' so the frontend can save it.
    """
    print("\n--- [API] /save_audit Called ---")
    audit_id = data.get("audit_id")
    file_name = data.get("file_name", "unknown_file")
    
    print(f"Received Payload: audit_id={audit_id}, file_name={file_name}")

    # --- AUTO GENERATE UUID IF MISSING ---
    if not audit_id:
        audit_id = str(uuid.uuid4())
        print(f"🔹 Generated New Audit ID: {audit_id}")
    
    repo = AuditRepository()
    try:
        success = repo.save_audit_session(audit_id, file_name)
        if success:
            print(f"✅ [API] Success: Session {audit_id} saved.")
            return {
                "status": "success", 
                "message": "Session saved", 
                "audit_id": audit_id
            }
        else:
            print(f"❌ [API] Failed: Could not save session {audit_id}")
            return {"status": "error", "message": "Failed to save session"}
    except Exception as e:
        print(f"❌ [API] Error: {e}")
        return {"status": "error", "message": str(e)}

# --- Save AI Result Endpoint ---
@app.post("/save_ai_result")
def save_ai_result(data: dict = Body(...)):
    """
    บันทึกผลลัพธ์จาก AI
    Expects: { "audit_id": "...", "step_id": 4, "result": ... }
    """
    print("\n--- [API] /save_ai_result Called ---")
    audit_id = data.get("audit_id")
    step_id = data.get("step_id")
    result = data.get("result", {})

    print(f"Received Payload: audit_id={audit_id}, step_id={step_id}")
    # print(f"Result Data: {result}") # Uncomment if you want to see the full JSON

    if not audit_id or not step_id:
        print("❌ [API] Error: Missing audit_id or step_id")
        return {"status": "error", "message": "Missing audit_id or step_id"}

    repo = AuditRepository()
    try:
        success = repo.save_step_log(audit_id, int(step_id), result)
        if success:
            print(f"✅ [API] Success: Step {step_id} logs saved for {audit_id}")
            return {"status": "success", "message": f"Step {step_id} data saved"}
        else:
            print(f"❌ [API] Failed: Could not save logs for {audit_id}")
            return {"status": "error", "message": "Failed to save data"}
    except Exception as e:
        print(f"❌ [API] Error: {e}")
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    if not os.path.exists("temp_uploads"):
        os.makedirs("temp_uploads")
    uvicorn.run(app, host="0.0.0.0", port=8000)