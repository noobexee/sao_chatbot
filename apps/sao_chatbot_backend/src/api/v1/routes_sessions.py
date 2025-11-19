from fastapi import APIRouter, HTTPException
from typing import List
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