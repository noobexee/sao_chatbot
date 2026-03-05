from fastapi import APIRouter, Depends
from src.api.v1.models.chatbot import UpdateSessionRequest
from src.api.v1.models import APIResponse
from src.app.chatbot.chatbot import chatbot
from src.app.auth.authen import auth_manager as auth

router = APIRouter()

# ===== GET ALL SESSIONS =====
@router.get("/sessions", response_model=APIResponse)
def get_all_sessions(current_user=Depends(auth.get_current_user)):
    try:
        user_id = current_user["id"]

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


# ===== GET HISTORY =====
@router.get("/history/{session_id}", response_model=APIResponse)
def get_chat_history(session_id: str, current_user=Depends(auth.get_current_user)):
    try:
        user_id = current_user["id"]

        messages = chatbot.get_session_history(user_id, session_id)

        return APIResponse(
            success=True,
            message="History retrieved successfully",
            data={
                "session_id": session_id,
                "messages": messages
            }
        )
    except Exception as e:
        return APIResponse(
            success=False,
            message=f"Failed to fetch history: {str(e)}",
            data=None
        )


# ===== DELETE SESSION =====
@router.delete("/sessions/{session_id}", response_model=APIResponse)
def delete_session(session_id: str, current_user=Depends(auth.get_current_user)):
    try:
        user_id = current_user["id"]

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


# ===== UPDATE SESSION =====
@router.patch("/sessions/{session_id}", response_model=APIResponse)
def update_session(
    session_id: str,
    payload: UpdateSessionRequest,
    current_user=Depends(auth.get_current_user)
):
    try:
        user_id = current_user["id"]

        result = chatbot.update_session(
            user_id=user_id,
            session_id=session_id,
            title=payload.title,
            is_pinned=payload.is_pinned
        )

        if result["status"] == "error":
            return APIResponse(
                success=False,
                message=result["message"],
                data=None
            )

        return APIResponse(
            success=True,
            message="Updated successfully",
            data=None
        )

    except Exception as e:
        return APIResponse(
            success=False,
            message=str(e),
            data=None
        )