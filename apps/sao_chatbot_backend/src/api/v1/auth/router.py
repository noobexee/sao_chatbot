from fastapi import APIRouter
from src.api.v1.auth.auth import router

auth_router = APIRouter()

auth_router.include_router(router)