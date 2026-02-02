from fastapi import APIRouter, HTTPException
from pathlib import Path
import uuid
from src.api.v1.merger.doc_manage import find_doc_dir_by_id
from src.app.llm.gemini import GeminiLLM
from src.app.manager.document import DocumentMeta, MergeRequest
from src.db.repositories.document_repository import DocumentRepository

router = APIRouter()
MOCK_DIR = Path("mock")

def load_text_and_meta(doc_id: str) -> tuple[str, DocumentMeta, Path]:
    doc_dir = find_doc_dir_by_id(doc_id)
    if not doc_dir:
        raise HTTPException(404, f"Document {doc_id} not found")

    text_path = doc_dir / "text.txt"
    meta_path = doc_dir / "meta.json"

    if not text_path.exists():
        raise HTTPException(400, f"text.txt missing for {doc_id}")
    if not meta_path.exists():
        raise HTTPException(400, f"meta.json missing for {doc_id}")

    meta = DocumentMeta.model_validate_json(
        meta_path.read_text(encoding="utf-8")
    )

    return text_path.read_text(encoding="utf-8"), meta, doc_dir

PROMPT_TEXT = """
  รวมเอกสาร {{AMEND_YEAR}} ({{AMEND_VERSION}}) เข้ากับเอกสาร {{BASE_YEAR}} 
  โดยให้เอกสาร {{AMEND_YEAR}} ({{AMEND_VERSION}}) เป็นตัวแก้ไขเอกสาร {{BASE_YEAR}}

  เงื่อนไข:
  1) จงอ่านเนื้อหาทั้งสองฉบับและรวมตามหลักกฎหมายเท่านั้น  
  2) ห้ามดัดแปลง เปลี่ยนคำศัพท์ หรือเรียบเรียงใหม่ ไม่ว่ากรณีใด  
  3) ให้แก้ไขเฉพาะส่วนที่ระบุไว้ในเอกสาร {{AMEND_YEAR}} ({{AMEND_VERSION}})  
  4) โครงสร้างหลักของเอกสารต้องยึดตามเอกสาร {{BASE_YEAR}}  
  5) ข้อความในปี {{BASE_YEAR}} ที่ถูกยกเลิกให้ลบออกทั้งหมด  
  6) ข้อความในปี {{BASE_YEAR}} ที่ถูกแก้ไขให้ลบออกทั้งหมด  

  การทำเครื่องหมายการเปลี่ยนแปลง (เคร่งครัด):
  - ให้ใส่อ้างอิง **เฉพาะท้ายวรรค/บรรทัดที่มีการเปลี่ยนแปลงเท่านั้น**
  - ห้ามใส่อ้างอิงในหัวข้อ ชื่อข้อ ชื่อหมวด หรือบรรทัดที่ไม่มีการเปลี่ยนแปลง
  - ห้ามใส่อ้างอิงซ้ำหลายครั้งในวรรคเดียว

  กรณีเพิ่มข้อความ:
  - ทุกวรรค/บรรทัดที่ **เพิ่มใหม่** ลงในเอกสาร {{BASE_YEAR}} 
    โดยเอกสาร {{AMEND_YEAR}} ({{AMEND_VERSION}})
    และมีคำสั่งนำหน้าว่า  
    "ให้เพิ่มความต่อไปนี้เป็นวรรค y ของข้อ x ของระเบียบสำนักงานการตรวจเงินแผ่นดินว่าด้วย การตรวจสอบการปฏิบัติตามกฎหมาย"  
    ให้ใส่ข้อความ  
    “(เพิ่มเติมโดย{{AMEND_VERSION}} พ.ศ. {{AMEND_YEAR}})”  
    **ต่อท้ายวรรค/บรรทัดนั้นเท่านั้น**

  กรณีแก้ไขข้อความ:
  - ทุกวรรค/บรรทัดที่ **ถูกแก้ไข** จากเอกสาร {{BASE_YEAR}} 
    โดยเอกสาร {{AMEND_YEAR}} ({{AMEND_VERSION}})
    และมีคำสั่งนำหน้าว่า  
    "ให้ยกเลิกความในข้อ x ของระเบียบสำนักงานการตรวจเงินแผ่นดินว่าด้วย การตรวจสอบการปฏิบัติตามกฎหมาย และให้ใช้ความต่อไปนี้แทน"  
    ให้ใส่ข้อความ  
    “(ยกเลิกโดย{{AMEND_VERSION}} พ.ศ. {{AMEND_YEAR}})”  
    **ต่อท้ายวรรค/บรรทัดนั้นเท่านั้น**

  ข้อห้าม (สำคัญมาก):
  - ห้ามใส่อ้างอิงในบรรทัดที่ไม่ได้ถูกเพิ่มหรือแก้ไข  
  - ห้ามใส่อ้างอิงในบรรทัดที่ถูกยกเลิกแล้ว  
  - ห้ามย้ายตำแหน่งอ้างอิงไปไว้ต้นบรรทัดหรือบรรทัดถัดไป  

  กรณีพิเศษ:
  - ข้อความที่ **ไม่มี** คำสั่งนำหน้าดังต่อไปนี้  
    1) "ให้เพิ่มความต่อไปนี้เป็นวรรค y ของข้อ x ของระเบียบสำนักงานการตรวจเงินแผ่นดินว่าด้วย การตรวจสอบการปฏิบัติตามกฎหมาย"  
    2) "ให้ยกเลิกความในข้อ x ของระเบียบสำนักงานการตรวจเงินแผ่นดินว่าด้วย การตรวจสอบการปฏิบัติตามกฎหมาย และให้ใช้ความต่อไปนี้แทน"  

    ให้นำข้อความนั้นไปจัดไว้ **ท้ายเอกสารเท่านั้น**  
    และ **ห้ามเปลี่ยนเลขข้อเดิม**
  """

@router.put("/merge")
def merge_documents(payload: MergeRequest):
    repo = DocumentRepository()

    # ---------- load texts ----------
    base_text = repo.get_text(payload.base_doc_id)
    amend_text = repo.get_text(payload.amend_doc_id)

    # ---------- merge logic ----------
    if payload.merge_mode == "replace_all":
        merged_text = amend_text
    else:
        llm = GeminiLLM()
        response = llm.invoke(
            system_prompt="คุณเป็นผู้เชี่ยวชาญด้านกฎหมายและการรวมเอกสารตามหลักนิติกรรม",
            prompt=PROMPT_TEXT,
            txt_files=[
                base_text.encode("utf-8"),
                amend_text.encode("utf-8"),
            ],
            mime_types=["text/plain", "text/plain"],
        )
        merged_text = response.content

    # ---------- persist snapshot ----------
    try:
        result = repo.merge_documents(
            base_doc_id=payload.base_doc_id,
            amend_doc_id=payload.amend_doc_id,
            merge_mode=payload.merge_mode,
            merged_text=merged_text,
        )
    except ValueError as e:
        raise HTTPException(404, str(e))

    return {
        "status": "success",
        **result,
        "text_endpoint": f"/doc/{result['id']}/text",
        "meta_endpoint": f"/doc/{result['id']}/meta",
    }
