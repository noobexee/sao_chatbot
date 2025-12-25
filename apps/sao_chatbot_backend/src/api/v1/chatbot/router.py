from fastapi import APIRouter
from src.api.v1.chatbot.chatbot import router as rag_router
from src.api.v1.chatbot.sessions import router as session_router

chatbot_router = APIRouter()

chatbot_router.include_router(rag_router)
chatbot_router.include_router(session_router)