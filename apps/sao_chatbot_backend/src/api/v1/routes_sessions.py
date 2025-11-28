from fastapi import APIRouter, HTTPException
from typing import List
from .models.chat import UpdateSessionRequest
from src.api.v1.models import APIResponse
from src.app.services.rag_service import rag_service

router = APIRouter()
@router.get("/sessions/{user_id}", response_model=APIResponse)
def get_all_sessions(user_id: int):
    try:
        sessions = rag_service.get_user_sessions(user_id)
        return APIResponse(
            success=True,
            message="Sessions retrieved successfully",
            data=sessions
        )
    except Exception as e:
        return APIResponse(
            success=False,
            message=f"Failed to fetch sessions: {str(e)}",
            data=None
        )
    
@router.get("/history/{user_id}/{session_id}", response_model=APIResponse)
def get_chat_history(user_id: int, session_id: str):
    try:
        messages = rag_service.get_session_history(user_id, session_id)
        
        history_data = {
            "session_id": session_id,
            "messages": messages
        }

        return APIResponse(
            success=True,
            message="History retrieved successfully",
            data=history_data
        )
    except Exception as e:
        return APIResponse(
            success=False,
            message=f"Failed to fetch history: {str(e)}",
            data=None
        )
    
@router.delete("/sessions/{user_id}/{session_id}", response_model=APIResponse)
def delete_session(user_id: int, session_id: str):
    try:
        result = rag_service.delete_session_history(user_id, session_id)
        
        if result.get("status") == "error":
             return APIResponse(
                success=False,
                message=result.get("message", "Unknown error"),
                data=None
            )
            
        return APIResponse(
            success=True,
            message=result.get("message", "Session deleted successfully"),
            data=None
        )
    except Exception as e:
        return APIResponse(
            success=False,
            message=f"Failed to delete session: {str(e)}",
            data=None
        )
@router.patch("/sessions/{user_id}/{session_id}", response_model=APIResponse)
def update_session(user_id: int, session_id: str, payload: UpdateSessionRequest):
    try:
        result = rag_service.update_session(
            user_id=user_id, 
            session_id=session_id, 
            title=payload.title, 
            is_pinned=payload.is_pinned
        )
        
        if result["status"] == "error":
             return APIResponse(success=False, message=result["message"], data=None)
            
        return APIResponse(success=True, message="Updated successfully", data=None)
    except Exception as e:
        return APIResponse(success=False, message=str(e), data=None)