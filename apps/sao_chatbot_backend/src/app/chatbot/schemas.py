from typing import Any, Dict, List
from pydantic import BaseModel

class RAGResponse(BaseModel):
    answer: str
    ref: List[str] = []
