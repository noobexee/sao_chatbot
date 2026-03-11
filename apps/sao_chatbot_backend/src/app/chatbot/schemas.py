from typing import Dict, List, Optional
from pydantic import BaseModel

class RAGResponse(BaseModel):
    answer: str
    ref: Dict[str, Optional[str]] = []
