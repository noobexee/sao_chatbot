from datetime import date
from typing import Optional, List
from pydantic import BaseModel

class DocumentMeta(BaseModel):
    title: str # law_name
    type: str # doc_type
    announce_date: date
    effective_date: date
    version: int = None # 1 if first version(new law), +1 for each amend
    is_snapshot: bool = False #True if got generated from merge (no pdf)
    is_latest: bool = False #True if its latest (for versioning)
    related_form_id: Optional[List[str]] = None #related form (table) for user upload

class MergeRequest(BaseModel):
    base_doc_id: str
    amend_doc_id: str
    merge_mode: str 
