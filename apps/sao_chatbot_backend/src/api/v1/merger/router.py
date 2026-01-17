from fastapi import APIRouter
from src.api.v1.merger.merger import router

merger_router = APIRouter()

merger_router.include_router(router)