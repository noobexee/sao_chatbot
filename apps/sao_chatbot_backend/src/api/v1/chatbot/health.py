from fastapi import APIRouter

router = APIRouter()

@router.get("/", summary="Health Check", tags=["Health"])
async def health_check():
    return {"status": "ok", "message": "Server is running"}