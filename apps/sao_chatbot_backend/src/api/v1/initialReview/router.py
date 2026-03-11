from fastapi import APIRouter
from src.api.v1.initialReview.initialReview_controller import router

review_router = APIRouter()

review_router.include_router(router)
