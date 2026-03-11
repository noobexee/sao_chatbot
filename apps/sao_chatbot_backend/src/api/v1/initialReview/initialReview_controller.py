import uuid
from typing import Optional
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Form, Query
from src.app.InitialReview.InitialReview_service import initial_review 
from src.app.InitialReview.InitialReviewSchemas import SaveResultRequest
from src.app.InitialReview.InitialReview_matcher import agency_matcher
from src.app.auth.authen import auth_manager as auth

router = APIRouter()

@router.post("/ocr")
async def ocr_document(
    file: UploadFile = File(...),
):
    try:
        result = await initial_review.ocr_document_logic(file)
        return result
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.post("/analyze")
async def analyze_document(
    file: UploadFile = File(...),
    session_id: Optional[str] = Form(default=None),
    current_user = Depends(auth.get_current_user),
):
    try:
        current_session_id = session_id if session_id else str(uuid.uuid4())

        result = await initial_review.analyze_document_logic(file)

        if "data" in result:
            result["session_id"] = current_session_id
            result["user_id"] = current_user["id"]

        return result

    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.get("/search_agency")
def manual_search_agency(q: str = Query(..., description="คำค้นหาชื่อหน่วยงาน")):
    if not agency_matcher:
        raise HTTPException(status_code=500, detail="Agency Matcher is not available")

    result = agency_matcher.search_agency(q)
    return result


@router.post("/save_result")
def save_ai_result(
    request: SaveResultRequest,
    current_user = Depends(auth.get_current_user),
):
    try:
        success = initial_review.save_criteria_log(
            user_id=current_user["id"],
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


# Sessions
@router.get("/sessions")
def get_user_sessions(
    current_user = Depends(auth.get_current_user),
):
    return initial_review.get_user_sessions(current_user["id"])


@router.get("/sessions/{session_id}")
def get_session_details(
    session_id: str,
    current_user = Depends(auth.get_current_user),
):
    return initial_review.get_review_by_session(current_user["id"], session_id)


@router.delete("/sessions/{session_id}")
def delete_session(
    session_id: str,
    current_user = Depends(auth.get_current_user),
):
    success = initial_review.delete_session(current_user["id"], session_id)

    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete session")

    return {"status": "success", "message": "Session deleted"}


# Summary
@router.get("/{session_id}/summary")
def get_review_summary(
    session_id: str,
    current_user = Depends(auth.get_current_user),
):
    return initial_review.get_InitialReview_summary(
        user_id=current_user["id"],
        InitialReview_id=session_id
    )
