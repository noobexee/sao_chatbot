from pydantic import BaseModel
from fastapi import UploadFile, File
from typing import List, Optional

class InitialReviewRequest(BaseModel):
    """
    Payload sent when a user sends a new message via POST /chat.
    """
    user_id: int
    file: any
