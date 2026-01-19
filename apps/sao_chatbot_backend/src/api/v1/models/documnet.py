from datetime import date
from typing import Optional
from openai import BaseModel   

class DocumentMeta(BaseModel):
    title: str
    type: str
    valid_from: date
    valid_until: Optional[date] = None
    version: Optional[str] = None
    is_snapshot: bool = False #True if got generated from merge
    got_updated: bool = False #True on got updated from merge
    is_first_version: bool #True if this is the first version of the document
