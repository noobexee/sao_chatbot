from fastapi import APIRouter

router = APIRouter()

#route http://localhost:8000/api/v1/chatbot
@router.get("/", summary="Health Check", tags=["Health"])
async def health_check():
    return {"status": "ok", "message": "Server is running"}