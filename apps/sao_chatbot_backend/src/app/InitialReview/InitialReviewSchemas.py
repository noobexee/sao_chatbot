from pydantic import BaseModel, Field
from typing import Optional, Dict, Any

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