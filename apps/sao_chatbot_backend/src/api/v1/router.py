from fastapi import APIRouter
from src.api.v1.chatbot.router import chatbot_router
from src.api.v1.merger.router import merger_router
from src.api.v1.initialreview.router import review_router
from src.api.v1.auth.router import auth_router

api_router = APIRouter()

api_router.include_router(chatbot_router, prefix="/chatbot", tags=["Chatbot"])
api_router.include_router(merger_router, prefix="/merger", tags=["Merger"])
api_router.include_router(review_router, prefix="/InitialReview", tags=["InitialReview"])
api_router.include_router(auth_router, prefix="/auth", tags=["Auth"])
