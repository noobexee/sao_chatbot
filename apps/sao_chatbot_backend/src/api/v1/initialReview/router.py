from fastapi import APIRouter
from src.api.v1.initialreview.initialReview_controller import router

review_router = APIRouter()

review_router.include_router(router)
