from fastapi import APIRouter, UploadFile, File, HTTPException, Body, Depends
from fastapi.responses import StreamingResponse
from src.app.audit.audit_service import AuditService

router = APIRouter(prefix="/audit", tags=["Audit Process"])

def get_audit_service():
    return AuditService()

# --- 1. Upload Document ---
@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    service: AuditService = Depends(get_audit_service)
):
    try:
        result = await service.process_upload(file)
        return result
    except Exception as e:
        return {"status": "error", "message": str(e)}

# --- 2. Analyze Document (AI) ---
@router.post("/analyze")
async def analyze_document(
    file: UploadFile = File(...),
    service: AuditService = Depends(get_audit_service)
):
    try:
        result = await service.analyze_document_logic(file)
        return result
    except Exception as e:
        return {"status": "error", "message": str(e)}

# --- 3. Get Info ---
@router.get("/{audit_id}/info")
def get_audit_info(
    audit_id: str,
    service: AuditService = Depends(get_audit_service)
):
    info = service.get_audit_info(audit_id)
    if not info:
        raise HTTPException(status_code=404, detail="Audit ID not found")
    return {"status": "success", "data": info}

# --- 4. Get File (Stream) ---
@router.get("/{audit_id}/file")
def get_audit_file(
    audit_id: str,
    service: AuditService = Depends(get_audit_service)
):
    try:
        file_stream, media_type = service.get_file_stream(audit_id)
        return StreamingResponse(file_stream, media_type=media_type)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="File content missing")
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

# --- 5. Save AI Result ---
@router.post("/save_result")
def save_ai_result(
    data: dict = Body(...),
    service: AuditService = Depends(get_audit_service)
):
    audit_id = data.get("audit_id")
    step_id = data.get("step_id")
    result = data.get("result", {})

    if not audit_id or not step_id:
        raise HTTPException(status_code=400, detail="Missing audit_id or step_id")

    success = service.save_ai_feedback(audit_id, step_id, result)
    if success:
        return {"status": "success", "message": "Saved successfully"}
    return {"status": "error", "message": "Failed to save data"}