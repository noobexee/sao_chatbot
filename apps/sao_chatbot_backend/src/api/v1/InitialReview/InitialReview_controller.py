import uuid
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Body
from src.app.InitialReview.InitialReview_service import InitialReviewService
from src.app.InitialReview.InitialReviewSchemas import SaveResultRequest

router = APIRouter(tags=["InitialReview Process"])

def get_InitialReview_service():
    return InitialReviewService()

@router.post("/ocr")
async def ocr_document(
    file: UploadFile = File(...),
    service: InitialReviewService = Depends(get_InitialReview_service)
):
    try:
        result = await service.ocr_document_logic(file)
        return result
    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.post("/analyze")
async def analyze_document(
    file: UploadFile = File(...),
    service: InitialReviewService = Depends(get_InitialReview_service)
):
    try:
        session_id = str(uuid.uuid4())
        
        result = await service.analyze_document_logic(file)
        
        if "data" in result:
            result["session_id"] = session_id
            
        return result
    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.post("/save_result")
def save_ai_result(
    data: dict = Body(...),
    service: InitialReviewService = Depends(get_InitialReview_service)
):
    try:
        session_id = data.get("session_id") or data.get("InitialReview_id")
        user_id = data.get("user_id", "anonymous")
        criteria_id = data.get("criteria_id")
        result_data = data.get("result", {})
        feedback = data.get("feedback")

        if not session_id or not criteria_id:
            raise HTTPException(status_code=400, detail="Missing session_id or criteria_id")

        success = service.save_criteria_log(
            user_id=user_id,
            session_id=session_id,
            criteria_id=int(criteria_id),
            ai_result=result_data,
            feedback=feedback
        )
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to save to database")
            
        return {"status": "success", "message": "Log saved successfully"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))