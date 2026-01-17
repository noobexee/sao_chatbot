from fastapi import APIRouter
from api.v1.merger.doc_manage import doc_manage_router
from api.v1.merger.merger import merger_router

router = APIRouter()

router.include_router(doc_manage_router)
router.include_router(merger_router)