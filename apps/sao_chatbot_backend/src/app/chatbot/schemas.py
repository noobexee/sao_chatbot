from typing import Dict, List
from pydantic import BaseModel

class RAGResponse(BaseModel):
    answer: str
    ref: Dict[str, str] = []
