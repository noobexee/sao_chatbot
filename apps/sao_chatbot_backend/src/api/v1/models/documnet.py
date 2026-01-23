from datetime import date
from typing import Optional
from openai import BaseModel   

class DocumentMeta(BaseModel):
    title: str
    type: str
    announce_date: date
    effective_date: date
    version: Optional[str] = None
    is_snapshot: bool = False #True if got generated from merge
    is_latest: bool = False #True if its latest
    is_first_version: bool #True if this is the first version of the document (new type new title)

class MergeRequest(BaseModel):
    base_doc_id: str
    amend_doc_id: str
