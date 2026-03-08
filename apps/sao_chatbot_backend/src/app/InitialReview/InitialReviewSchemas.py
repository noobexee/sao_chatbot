from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

class SaveResultRequest(BaseModel):
    """
    Schema สำหรับรับข้อมูลการบันทึกผลการตรวจสอบแต่ละ Criteria (ใช้ใน /save_result)
    """
    user_id: str = Field(default="anonymous", description="รหัสผู้ใช้งาน (User ID)")
    session_id: str = Field(..., description="รหัสเซสชันของการตรวจเอกสารฉบับนี้ (Session ID)")
    criteria_id: int = Field(..., description="หมายเลขข้อ Criteria (1-8)")
    result: Dict[str, Any] = Field(..., description="ข้อมูลผลลัพธ์จาก AI หรือข้อมูลที่มนุษย์แก้ไข")
    feedback: Optional[str] = Field(default=None, description="Feedback จากผู้ใช้ ('up' = ถูก, 'down' = ผิด)")

class SessionResponse(BaseModel):
    """
    (Optional) Schema สำหรับส่งข้อมูล Session กลับไปให้หน้าบ้าน
    """
    session_id: str
    last_updated: str
    criteria_count: int

from pydantic import BaseModel
from typing import Optional, List, Dict

class ReviewSummary(BaseModel):
    OCR_text: Optional[str] = None

    criteria_1: Optional[bool] = None
    criteria_2: Optional[bool] = None
    criteria_3: Optional[bool] = None

    # size 4
    criteria_4: Optional[List[bool]] = None

    criteria_5: Optional[bool] = None

    # size 3 (first can be None)
    criteria_6: Optional[List[Optional[bool]]] = None

    # if True must have value, if False value must be None
    criteria_7: Optional[Dict[bool, Optional[str]]] = None

    # True -> reason string
    criteria_8: Optional[Dict[bool, str]] = None