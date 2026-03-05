import uuid
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Form
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
    user_id: str = Form(default="anonymous"),
    service: InitialReviewService = Depends(get_InitialReview_service)
):
    try:
        session_id = str(uuid.uuid4())
        
        result = await service.analyze_document_logic(file)
        
        if "data" in result:
            result["session_id"] = session_id
            result["user_id"] = user_id
            
        return result
    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.post("/save_result")
def save_ai_result(
    request: SaveResultRequest, # 🟢 ใช้ Schema แทน dict ลอยๆ
    service: InitialReviewService = Depends(get_InitialReview_service)
):
    try:
        success = service.save_criteria_log(
            user_id=request.user_id,
            session_id=request.session_id,
            criteria_id=request.criteria_id,
            ai_result=request.result,
            feedback=request.feedback
        )
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to save to database")
            
        return {"status": "success", "message": "Log saved successfully"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/sessions/{user_id}")
def get_user_sessions(
    user_id: str, 
    service: InitialReviewService = Depends(get_InitialReview_service)
):
    """ดึงประวัติเอกสารทั้งหมดที่เคยตรวจของ User นี้"""
    return service.get_all_sessions(user_id)

@router.get("/sessions/{user_id}/{session_id}")
def get_session_details(
    user_id: str, 
    session_id: str, 
    service: InitialReviewService = Depends(get_InitialReview_service)
):
    """ดึงรายละเอียดผลการตรวจสอบทั้งหมดใน Session (เอกสาร) นั้นๆ"""
    return service.get_review_by_session(user_id, session_id)
    
@router.delete("/sessions/{user_id}/{session_id}")
def delete_session(
    user_id: str, 
    session_id: str, 
    service: InitialReviewService = Depends(get_InitialReview_service)
):
    """ลบประวัติการตรวจเอกสาร (Session)"""
    success = service.delete_session(user_id, session_id)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete session")
    return {"status": "success", "message": "Session deleted"}