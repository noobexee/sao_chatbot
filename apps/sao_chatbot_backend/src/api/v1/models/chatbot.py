from pydantic import BaseModel
from typing import List, Optional

class ChatRequest(BaseModel):
    """
    Payload sent when a user sends a new message via POST /chat.
    """
    user_id: int
    session_id: str
    query: str


class SessionItem(BaseModel):
    """
    Used for the list of chats in the sidebar (GET /sessions).
    """
    session_id: str
    title: str       
    created_at: str

class HistoryMessage(BaseModel):
    """
    A single message bubble in the UI.
    """
    role: str        
    content: str
    created_at: str

class HistoryResponse(BaseModel):
    """
    The full conversation history loaded when clicking a sidebar item.
    (GET /history)
    """
    session_id: str
    messages: List[HistoryMessage]

class UpdateSessionRequest(BaseModel):
    title: Optional[str] = None
    is_pinned: Optional[bool] = None