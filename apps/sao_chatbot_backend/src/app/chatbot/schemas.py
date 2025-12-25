from typing import Any, Dict, List
from pydantic import BaseModel

class RAGResponse(BaseModel):
    answer: str
    model_used: str
    ref: List[str] = []
