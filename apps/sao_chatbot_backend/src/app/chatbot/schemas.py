from typing import Dict, List, Optional
from pydantic import BaseModel, Field

class RAGResponse(BaseModel):
    answer: str
    ref: Dict[str, Optional[str]] = []

class LegalResponseSchema(BaseModel):
    answer_text: str = Field(description="The natural Thai response starting with 'จากข้อ... ของระเบียบ...'")
    used_law_names: List[str] = Field(description="List of exact law_names or guideline_names from the context that were used to answer the question.")

class FileResponseSchema(BaseModel):
    answer_text: str = Field(description="A polite, formal Thai response (e.g., 'ขออนุญาตนำส่งเอกสาร').")
    target_files: List[str] = Field(description="List of exact filenames found. Empty list if none.")