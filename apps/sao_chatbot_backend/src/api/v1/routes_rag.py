from fastapi import APIRouter, HTTPException
from src.api.v1.models.chat import ChatRequest
from src.api.v1.models import APIResponse
from src.app.services.rag_service import rag_service

router = APIRouter()

@router.post("/query", response_model=APIResponse)
async def run_rag(request: ChatRequest):
    try:
        answer_response = await rag_service.answer_question(
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