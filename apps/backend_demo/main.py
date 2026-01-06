from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from services import typhoon_service
from agents import audit_agents
import shutil
import os
import uvicorn
import asyncio 

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/analyze")
async def analyze_document(file: UploadFile = File(...)):
    temp_path = f"temp_uploads/{file.filename}"
    
    try:
        # 1. Save File
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        print(f"Processing: {temp_path}")

        # 2. Extract Text (using standard libs/Typhoon)
        extracted_text = typhoon_service.extract_text(temp_path)
        print(f"Extracted {len(extracted_text)} chars. Sending to Gemini Agents...")
        
        # 3. Call Gemini Agents (Parallel)
        # We run both prompts at the same time to save time
        step4_task = asyncio.to_thread(audit_agents.agent_step4_sufficiency, extracted_text)
        step6_task = asyncio.to_thread(audit_agents.agent_step6_complainant, extracted_text)
        
        step4_ai_result, step6_ai_result = await asyncio.gather(step4_task, step6_task)

        # 4. Format Results for Frontend
        
        # Step 4 Processing
        if step4_ai_result:
            step4_response = {
                "status": step4_ai_result.get("status", "fail"),
                "title": step4_ai_result.get("title", "การวิเคราะห์ล้มเหลว"),
                "reason": step4_ai_result.get("reason", "-"),
                "details": step4_ai_result.get("details", {})
            }
        else:
            step4_response = {"status": "fail", "title": "AI Error", "details": {}}

        # Step 6 Processing
        if step6_ai_result:
            people_list = step6_ai_result.get("people", [])
            # Determine Pass/Fail based on if a "Complainant" exists
            has_complainant = any(p['role'] == 'ผู้ร้องเรียน' for p in people_list)
            
            step6_response = {
                "status": "success" if has_complainant else "fail",
                "title": "รายละเอียดของผู้ร้องเรียน",
                "people": people_list
            }
        else:
            step6_response = {"status": "fail", "title": "AI Error", "people": []}

        # 5. Cleanup
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

if __name__ == "__main__":
    if not os.path.exists("temp_uploads"):
        os.makedirs("temp_uploads")
    # Using 8080 to match your frontend config
    uvicorn.run(app, host="0.0.0.0", port=8080)