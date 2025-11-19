from pydantic import BaseModel

class RAGRequest(BaseModel):
    session_id : str
    user_id :str
    query: str
