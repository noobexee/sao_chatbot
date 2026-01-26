from fastapi import APIRouter
from src.api.v1.InitialReview.InitialReview_controller import router as InitialReview_controller_router

api_router = APIRouter()

api_router.include_router(InitialReview_controller_router)