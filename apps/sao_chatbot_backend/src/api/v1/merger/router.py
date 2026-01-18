from fastapi import APIRouter
from src.api.v1.merger.doc_manage import router as doc_router
from src.api.v1.merger.merger import router as merge_router

merger_router = APIRouter()

merger_router.include_router(doc_router)
merger_router.include_router(merge_router)