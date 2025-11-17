# main.py
import uvicorn
from fastapi import FastAPI

# 1. Initialize the FastAPI app
app = FastAPI(
    title="Test Server",
    description="A minimal server to test the FastAPI setup."
)

# 2. Create a test endpoint
@app.get("/", tags=["Health Check"])
async def root():
    """
    Root endpoint to check if the server is running.
    """
    return {"status": "ok", "message": "FastAPI server is running!"}

# 3. (Optional) Run the server directly with 'python main.py'
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)