from pydantic import BaseModel

class RAGResponse(BaseModel):
    answer: str
    model_used: str
