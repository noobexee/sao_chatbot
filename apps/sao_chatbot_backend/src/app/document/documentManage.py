from typing import Optional, List
from datetime import date ,timedelta
from src.app.document.documentSchemas import DocumentMeta
from src.db.repositories.document_repository import DocumentRepository
from src.app.document.documentUpdate import DocumentUpdater
from src.app.service.ocr_service import run_ocr_and_update_db
from src.app.llm.gemini import GeminiLLM

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

class DocumentManager:

    def __init__(self):
        self.repo = DocumentRepository()
        self.updater = DocumentUpdater()
        self.llm = GeminiLLM()

    def list_documents(self):
        return self.repo.list_documents()

    def get_original_pdf(self, doc_id: str):
        return self.repo.get_original_pdf(doc_id)

    def get_status(self, doc_id: str):
        return self.repo.get_status(doc_id)

    def get_text(self, doc_id: str) -> str:
        return self.repo.get_text(doc_id)

    def get_metadata(self, doc_id: str) -> DocumentMeta:
        return self.repo.get_metadata(doc_id)

    # ---------- Create ----------

    def create_document(
        self,
        *,
        doc_type: str,
        title: Optional[str],
        announce_date: date,
        effective_date: date,
        is_first_version: bool,
        previous_doc_id: Optional[str],
        main_file_name: str,
        main_file_bytes: bytes,
        related_files: Optional[List[tuple[str, bytes]]],
    ) -> dict:
        if previous_doc_id and is_first_version:
            raise ValueError("is_first_version cannot be true when previous_doc_id is provided")

        base_meta: Optional[DocumentMeta] = None

        if previous_doc_id:
            base_meta = self.repo.get_metadata(previous_doc_id)
            if not base_meta:
                raise ValueError("previous document not found")

        if base_meta:
            safe_type = base_meta.type
            derived_title = base_meta.title
            version = base_meta.version + 1

            self.repo.bump_version_and_invalidate_latest(safe_type, derived_title)
        else:
            safe_type = doc_type.strip().lower().replace(" ", "_")
            derived_title = title or main_file_name.rsplit(".", 1)[0]

            if is_first_version:
                version = 1
            else:
                version = self.repo.bump_version_and_invalidate_latest(
                    safe_type,
                    derived_title,
                )

        meta = DocumentMeta(
            title=derived_title,
            type=safe_type,
            announce_date=announce_date,
            effective_date=effective_date,
            version=version,
            is_snapshot=False,
            is_latest=True,
            related_form_id=[],
        )

        result = self.repo.save_document(
            doc_type=safe_type,
            title=derived_title,
            version=version,
            announce_date=announce_date,
            effective_date=effective_date,
            is_latest=True,
            meta=meta,
            main_file_name=main_file_name,
            main_file_bytes=main_file_bytes,
            related_files=related_files,
        )

        meta.related_form_id = result["related_form_id"]

        return {
            "id": result["id"],
            "title": meta.title,
            "version": meta.version,
            "related_form_id": meta.related_form_id,
        }
    
    def handle_ocr(self, *, doc_id: str, pdf_bytes: bytes):
        
        run_ocr_and_update_db(doc_id,pdf_bytes)

        text = self.repo.get_text(doc_id)
        meta = self.repo.get_metadata(doc_id)
        
        res = self.updater.new_document( 
            doc_data = meta, 
            doc_id = doc_id,
            text=text 
        )

        return res

    # ---------- Update ----------

    def edit_document(
        self,
        *,
        doc_id: str,
        title: str,
        type: str,
        announce_date: date,
        effective_date: Optional[date],
        text_content: str,
    ):

        meta_list = self.repo.get_metadata(doc_id)
        if not meta_list:
            raise ValueError("Document not found")

        meta_list.title = title.strip()
        meta_list.type = type.strip().lower().replace(" ", "_")
        meta_list.announce_date = announce_date
        meta_list.effective_date = effective_date

        self.repo.edit_doc(
            doc_id=doc_id,
            title=meta_list.title,
            type=meta_list.type,
            announce_date=meta_list.announce_date,
            effective_date=meta_list.effective_date,
            text_content=text_content,
            meta_json=[meta_list.model_dump(mode="json")],
        )

        res = self.updater.edit_document(
            doc_id=doc_id,
            doc_data=meta_list,
            text=text_content,
        )

        return res

    def merge_documents(
        self,
        *,
        base_doc_id: str,
        amend_doc_id: str,
        merge_mode: str,
    ) -> dict:

        base_text = self.repo.get_text(base_doc_id)
        amend_text = self.repo.get_text(amend_doc_id)

#        base_meta=self.repo.get_metadata(base_doc_id)
#        amend_meta=self.repo.get_metadata(amend_doc_id)

        if merge_mode == "replace_all":
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

        new = self.repo.merge_documents(
            base_doc_id=base_doc_id,
            amend_doc_id=amend_doc_id,
            merged_text=merged_text,
            merge_mode=merge_mode
        )
        meta = self.repo.get_metadata(new)
        self.updater.merge_documents(
            doc_data=meta,
            old_doc_id= base_doc_id,
            new_doc_id= amend_doc_id,
            text= merged_text,
            expire_date= meta.effective_date + timedelta(days=1),
        )
        return {"id": new}

    def delete_document(self, doc_id: str):
        self.repo.delete_document(doc_id)
        res = self.updater.delete_document(doc_id)
        return res

manager = DocumentManager()