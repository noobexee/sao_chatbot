from fastapi import APIRouter
from src.api.v1.audit.audit_controller import router as audit_controller_router

api_router = APIRouter()

api_router.include_router(audit_controller_router)