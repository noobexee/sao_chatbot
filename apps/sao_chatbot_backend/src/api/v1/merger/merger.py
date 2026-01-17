from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from src.app.llm.gemini import GeminiLLM

router = APIRouter()

@router.post("/merge")
async def merge_documents(
    base_file: UploadFile = File(...),
    amend_file: UploadFile = File(...),
    base_year: str = Form(...),
    amend_year: str = Form(...),
    amend_version: str = Form(...),
):
    if base_file.content_type != "text/plain" or amend_file.content_type != "text/plain":
        raise HTTPException(status_code=400, detail="Only .txt files are allowed")

    base_bytes = await base_file.read()
    amend_bytes = await amend_file.read()

    prompt = f"""
        รวมเอกสาร {amend_year} ({amend_version}) เข้ากับเอกสาร {base_year}
        โดยให้เอกสาร {amend_year} ({amend_version}) เป็นตัวแก้ไขเอกสาร {base_year}

        เงื่อนไข:
        1) จงอ่านเนื้อหาทั้งสองฉบับและรวมตามหลักกฎหมายเท่านั้น  
        2) ห้ามดัดแปลง เปลี่ยนคำศัพท์ หรือเรียบเรียงใหม่ ไม่ว่ากรณีใด  
        3) ให้แก้ไขเฉพาะส่วนที่ระบุไว้ในเอกสาร {amend_year} ({amend_version})  
        4) โครงสร้างหลักของเอกสารต้องยึดตามเอกสาร {base_year}  
        5) ข้อความในปี {base_year} ที่ถูกยกเลิกให้ลบออกทั้งหมด  
        6) ข้อความในปี {base_year} ที่ถูกแก้ไขให้ลบออกทั้งหมด  

        การทำเครื่องหมายการเปลี่ยนแปลง (เคร่งครัด):
        - ให้ใส่อ้างอิง **เฉพาะท้ายวรรค/บรรทัดที่มีการเปลี่ยนแปลงเท่านั้น**
        - ห้ามใส่อ้างอิงในหัวข้อ ชื่อข้อ ชื่อหมวด หรือบรรทัดที่ไม่มีการเปลี่ยนแปลง
        - ห้ามใส่อ้างอิงซ้ำหลายครั้งในวรรคเดียว

        กรณีเพิ่มข้อความ:
        - ให้ใส่ “(เพิ่มเติมโดย{amend_version} {amend_year})” ต่อท้ายวรรคเท่านั้น

        กรณีแก้ไขข้อความ:
        - ให้ใส่ “(ยกเลิกโดย{amend_version} {amend_year})” ต่อท้ายวรรคเท่านั้น

        กรณีพิเศษ:
        - ข้อความที่ไม่มีคำสั่งนำหน้า
        ให้นำไปจัดไว้ **ท้ายเอกสารเท่านั้น**
        และ **ห้ามเปลี่ยนเลขข้อเดิม**
"""

    llm = GeminiLLM()
    response = llm.invoke(
        system_prompt="คุณเป็นผู้เชี่ยวชาญด้านกฎหมายและการรวมเอกสารตามหลักนิติกรรม",
        prompt=prompt,
        txt_files=[base_bytes, amend_bytes],
        mime_types=["text/plain", "text/plain"],
    )
    return {
        "status": "success",
        "merged_text": response.content
    }
