from fastapi import APIRouter
from src.api.v1.chatbot.router import chatbot_router
from src.api.v1.merger.router import merger_router
from src.api.v1.InitialReview.router import InitialReview_controller_router

api_router = APIRouter()

api_router.include_router(chatbot_router, prefix="/chatbot", tags=["Chatbot"])
api_router.include_router(merger_router, prefix="/merger", tags=["Merger"])
api_router.include_router(InitialReview_controller_router, prefix="/InitialReview", tags=["InitialReview"])