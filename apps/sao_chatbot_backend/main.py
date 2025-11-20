from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.api import rag_router, health_router, session_router

app = FastAPI(
    title="RAG Backend API",
    description="API for Retrieval Augmented Generation",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware, 
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"], 
    allow_headers=["*"],
)

@app.get("/", tags=["Health Check"])
def health_check():
    return {"status": "running", "message": "RAG Backend is up!"}

app.include_router(rag_router, prefix="/api/v1", tags=["RAG"])
app.include_router(health_router, prefix="/api/v1/health")
app.include_router(session_router, prefix="/api/v1", tags=["History"])