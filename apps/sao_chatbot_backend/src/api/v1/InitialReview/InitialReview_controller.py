from fastapi import APIRouter, UploadFile, File, HTTPException, Body, Depends
from fastapi.responses import StreamingResponse
from src.app.InitialReview.InitialReview_service import InitialReviewService

router = APIRouter(tags=["InitialReview Process"])

def get_InitialReview_service():
    return InitialReviewService()

# --- 2. Analyze Document (AI) ---
@router.post("/analyze")
async def analyze_document(
    file: UploadFile = File(...),
    service: InitialReviewService = Depends(get_InitialReview_service)
):
    try:
        result = await service.analyze_document_logic(file)
        return result
    except Exception as e:
        return {"status": "error", "message": str(e)}

# --- 5. Save AI Result ---
@router.post("/save_result")
def save_ai_result(
    data: dict = Body(...),
    service: InitialReviewService = Depends(get_InitialReview_service)
):
    InitialReview_id = data.get("InitialReview_id")
    criteria_id = data.get("criteria_id")
    result = data.get("result", {})

    if not InitialReview_id or not criteria_id:
        raise HTTPException(status_code=400, detail="Missing InitialReview_id or criteria_id")

    success = service.save_ai_feedback(InitialReview_id, criteria_id, result)
    if success:
        return {"status": "success", "message": "Saved successfully"}
    return {"status": "error", "message": "Failed to save data"}