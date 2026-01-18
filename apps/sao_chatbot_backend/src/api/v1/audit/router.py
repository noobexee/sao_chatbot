from fastapi import APIRouter
from apps.sao_chatbot_backend.src.api.v1.audit.audit_controller import router as audit_router

audit_router = APIRouter()

audit_router.include_router(audit_router)