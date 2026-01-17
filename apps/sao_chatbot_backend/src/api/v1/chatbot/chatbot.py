from fastapi import APIRouter, HTTPException
from src.api.v1.models.chatbot import ChatRequest
from src.api.v1.models import APIResponse
from src.app.chatbot.chatbot import chatbot

router = APIRouter()

#route http://localhost:8000/api/v1/chatbot/query
@router.post("/query", response_model=APIResponse)
async def run_rag(request: ChatRequest):
    try:
        answer_response = await chatbot.answer_question(
            user_id=request.user_id,
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