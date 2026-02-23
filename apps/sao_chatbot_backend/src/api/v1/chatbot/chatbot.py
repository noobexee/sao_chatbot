from fastapi import APIRouter, HTTPException, Depends
from src.api.v1.models.chatbot import ChatRequest
from src.api.v1.models import APIResponse
from src.app.chatbot.chatbot import chatbot
from src.app.auth.authen import auth_manager as auth

router = APIRouter()

# route http://localhost:8000/api/v1/chatbot/query
@router.post("/query", response_model=APIResponse)
async def run_rag(
    request: ChatRequest,
    current_user=Depends(auth.get_current_user) 
):
    try:
        answer_response = await chatbot.answer_question(
            user_id=current_user["id"], 
            session_id=request.session_id,
            query=request.query
        )

        return APIResponse(
            success=True,
            message="RAG successful",
            data=answer_response
        )

    except Exception as e:
        return APIResponse(
            success=False,
            message=f"Error processing RAG request: {str(e)}",
            data=None
        )