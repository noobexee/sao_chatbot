from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.api.v1.router import api_router 

app = FastAPI(
    title="RAG Backend API",
    description="API for Retrieval Augmented Generation and Audit Logging",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware, 
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"], 
    allow_headers=["*"],
)

@app.get("/", tags=["System"])
def root():
    return {"status": "running", "message": "RAG Backend is up!"}

app.include_router(api_router, prefix="/api/v1")