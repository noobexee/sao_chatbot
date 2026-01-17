from fastapi import APIRouter, HTTPException
from src.api.v1.models.chatbot import UpdateSessionRequest
from src.api.v1.models import APIResponse
from src.app.chatbot.chatbot import chatbot

router = APIRouter()

#route http://localhost:8000/api/v1/chatbot/sessions/userid  
#method GET
@router.get("/sessions/{user_id}", response_model=APIResponse)
def get_all_sessions(user_id: int):
    try:
        sessions = chatbot.get_user_sessions(user_id)
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

#route http://localhost:8000/api/v1/history/user_id/session_id
#method GET
@router.get("/history/{user_id}/{session_id}", response_model=APIResponse)
def get_chat_history(user_id: int, session_id: str):
    try:
        messages = chatbot.get_session_history(user_id, session_id)
        
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

#route http://localhost:8000/api/v1/sessions/user_id/session_id
#method DELETE
@router.delete("/sessions/{user_id}/{session_id}", response_model=APIResponse)
def delete_session(user_id: int, session_id: str):
    try:
        result = chatbot.delete_session_history(user_id, session_id)
        
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
    
#route http://localhost:8000/api/v1/sessions/user_id/session_id
#method PUT
@router.patch("/sessions/{user_id}/{session_id}", response_model=APIResponse)
def update_session(user_id: int, session_id: str, payload: UpdateSessionRequest):
    try:
        result = chatbot.update_session(
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