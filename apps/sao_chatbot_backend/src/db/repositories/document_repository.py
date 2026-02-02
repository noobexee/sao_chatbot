from pathlib import Path
from typing import Optional, List
from datetime import date
import uuid
import json
from src.db.connection import get_db_connection
from src.app.manager.document import DocumentMeta
from PyPDF2 import PdfReader, PdfWriter
import io

class DocumentRepository:

    def save_document(
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
        conn = None
        try:
            if previous_doc_id and is_first_version:
                raise ValueError("is_first_version cannot be true when previous_doc_id is provided")

            conn = get_db_connection()
            cur = conn.cursor()

            base_meta: Optional[DocumentMeta] = None

            if previous_doc_id:
                cur.execute(
                    "SELECT meta_json FROM documents WHERE id = %s",
                    (previous_doc_id,),
                )
                row = cur.fetchone()
                if not row:
                    raise ValueError("previous document not found")

                meta_list = row[0] or []
                if meta_list:
                    base_meta = DocumentMeta.model_validate(meta_list[-1])

            if base_meta:
                safe_type = base_meta.type
                derived_title = base_meta.title
                version = base_meta.version + 1

                cur.execute(
                    """
                    UPDATE documents
                    SET is_latest = FALSE
                    WHERE type = %s AND title = %s
                    """,
                    (safe_type, derived_title),
                )
            else:
                safe_type = doc_type.strip().lower().replace(" ", "_")
                derived_title = title or main_file_name.rsplit(".", 1)[0]

                if is_first_version:
                    version = 1
                else:
                    cur.execute(
                        """
                        SELECT COALESCE(MAX(version), 0)
                        FROM documents
                        WHERE type = %s AND title = %s
                        """,
                        (safe_type, derived_title),
                    )
                    version = cur.fetchone()[0] + 1

                    cur.execute(
                        """
                        UPDATE documents
                        SET is_latest = FALSE
                        WHERE type = %s AND title = %s
                        """,
                        (safe_type, derived_title),
                    )

            doc_id = str(uuid.uuid4())
            related_form_id: Optional[List[str]] = None

            if related_files:
                related_form_id = []
                for filename, content in related_files:
                    rel_id = str(uuid.uuid4())
                    related_form_id.append(rel_id)

                    cur.execute(
                        """
                        INSERT INTO document_files (id, document_id, file_name, file_data)
                        VALUES (%s, %s, %s, %s)
                        """,
                        (rel_id, doc_id, filename, content),
                    )

            meta = DocumentMeta(
                title=derived_title,
                type=safe_type,
                announce_date=announce_date,
                effective_date=effective_date,
                version=version,
                is_snapshot=False,
                is_latest=True,
                related_form_id=related_form_id,
            )
            meta_json = [meta.model_dump(mode="json")]
            print(meta_json)

            cur.execute(
                """
                INSERT INTO documents (
                    id,
                    type,
                    title,
                    version,
                    announce_date,
                    effective_date,
                    is_latest,
                    meta_json,
                    pdf_file_name,
                    pdf_file_data,
                    status,
                    created_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'processing', NOW())
                """,
                (
                    doc_id,
                    safe_type,
                    derived_title,
                    version,
                    announce_date,
                    effective_date,
                    True,
                    json.dumps(meta_json),
                    main_file_name,
                    main_file_bytes,
                ),
            )

            conn.commit()

            return {
                "id": doc_id,
                "title": meta.title,
                "version": meta.version,
                "related_form_id": meta.related_form_id,
            }

        except Exception:
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                conn.close()

    def list_documents(self) -> List[dict]:
        conn = None
        try:
            conn = get_db_connection()
            cur = conn.cursor()

            cur.execute(
                """
                SELECT
                    id,
                    meta_json,
                    status
                FROM documents
                ORDER BY created_at DESC
                """
            )

            docs = []

            for doc_id, meta_json, status in cur.fetchall():

                if not meta_json:
                    continue

                # --- normalize meta_json ---
                if isinstance(meta_json, list):
                    if not meta_json:
                        continue
                    meta_dict = meta_json[-1]
                else:
                    meta_dict = meta_json

                meta = DocumentMeta.model_validate(meta_dict)

                docs.append({
                    "id": doc_id,
                    **meta.model_dump(mode="json"),
                    "status": status,
                })

            cur.close()
            return docs

        finally:
            if conn:
                conn.close()


    def get_original_pdf(self, doc_id: str) -> tuple[str, bytes]:
        conn = None
        try:
            conn = get_db_connection()
            cur = conn.cursor()

            cur.execute(
                """
                SELECT pdf_file_name, pdf_file_data
                FROM documents
                WHERE id = %s
                """,
                (doc_id,),
            )

            row = cur.fetchone()
            if not row:
                raise ValueError("Document not found")

            file_name, file_data = row[0], row[1]

            if not file_data:
                raise ValueError("PDF not found")

            cur.close()
            return file_name, file_data

        finally:
            if conn:
                conn.close()

    def get_status(self, doc_id: str) -> dict:
        conn = None
        try:
            conn = get_db_connection()
            cur = conn.cursor()

            cur.execute(
                """
                SELECT
                    status,
                    current_page,
                    total_pages,
                    pages
                FROM documents
                WHERE id = %s
                """,
                (doc_id,),
            )

            row = cur.fetchone()
            if not row:
                raise ValueError("Document not found")

            status, current_page, total_pages, pages = row
            response = {"status": status}

            if status == "processing":
                if current_page is not None and total_pages is not None:
                    response.update({
                        "current_page": current_page,
                        "total_pages": total_pages,
                        "message": f"Processing Page {current_page}/{total_pages}",
                    })

            elif status == "done":
                if pages is not None:
                    response["pages"] = pages

            return response

        finally:
            if conn:
                conn.close()

    def edit_doc(
        self,
        *,
        doc_id: str,
        title: str,
        type: str,
        announce_date: date,
        effective_date: date | None,
        text_content: str,
    ) -> None:
        conn = None
        try:
            conn = get_db_connection()
            cur = conn.cursor()

            cur.execute(
                "SELECT meta_json FROM documents WHERE id = %s",
                (doc_id,),
            )
            row = cur.fetchone()
            if not row:
                raise ValueError("Document not found")

            meta_list = row[0] or []

            latest_meta = DocumentMeta.model_validate(meta_list[-1])

            latest_meta.title = title.strip()
            latest_meta.type = type.strip().lower().replace(" ", "_")
            latest_meta.announce_date = announce_date
            latest_meta.effective_date = effective_date

            meta_list.append(latest_meta.model_dump(mode="json"))

            cur.execute(
                """
                UPDATE documents
                SET
                    title = %s,
                    type = %s,
                    announce_date = %s,
                    effective_date = %s,
                    meta_json = %s,
                    text_content = %s,
                    updated_at = NOW()
                WHERE id = %s
                """,
                (
                    latest_meta.title,
                    latest_meta.type,
                    latest_meta.announce_date,
                    latest_meta.effective_date,
                    json.dumps(meta_list),
                    text_content,
                    doc_id,
                ),
            )

            conn.commit()

        except Exception:
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                conn.close()
       
    def get_metadata(self, doc_id: str) -> DocumentMeta:
        conn = None
        try:
            conn = get_db_connection()
            cur = conn.cursor()

            cur.execute(
                "SELECT meta_json FROM documents WHERE id = %s",
                (doc_id,),
            )
            row = cur.fetchone()
            if not row or not row[0]:
                raise ValueError("Document not found")

            meta_json = row[0]

            # --- normalize meta_json ---
            if isinstance(meta_json, list):
                if not meta_json:
                    raise ValueError("meta_json is empty list")
                meta_dict = meta_json[-1]
            else:
                meta_dict = meta_json

            return DocumentMeta.model_validate(meta_dict)

        finally:
            if conn:
                conn.close()


    def delete_document(self, doc_id: str) -> None:
        conn = None
        try:
            conn = get_db_connection()
            cur = conn.cursor()

            cur.execute(
                "SELECT 1 FROM documents WHERE id = %s",
                (doc_id,),
            )
            if not cur.fetchone():
                raise ValueError("Document not found")
            
            cur.execute(
                "DELETE FROM document_files WHERE document_id = %s",
                (doc_id,),
            )

            cur.execute(
                "DELETE FROM documents WHERE id = %s",
                (doc_id,),
            )

            conn.commit()

        except Exception as e:
            if conn:
                conn.rollback()
            raise e
        finally:
            if conn:
                conn.close()

    def get_text(self, doc_id: str) -> str:
        conn = None
        try:
            conn = get_db_connection()
            cur = conn.cursor()

            cur.execute(
                """
                SELECT text_content
                FROM documents
                WHERE id = %s
                """,
                (doc_id,),
            )

            row = cur.fetchone()
            if not row:
                raise ValueError("Document not found")

            text: Optional[str] = row[0]

            if text is None:
                raise ValueError("Text not ready")

            return text

        finally:
            if conn:
                conn.close()

    @staticmethod
    def merge_pdf_bytes(pdf1: bytes, pdf2: bytes) -> bytes:
        writer = PdfWriter()

        for data in (pdf1, pdf2):
            reader = PdfReader(io.BytesIO(data))
            for page in reader.pages:
                writer.add_page(page)

        out = io.BytesIO()
        writer.write(out)
        return out.getvalue()

    def merge_documents(
        self,
        *,
        base_doc_id: str,
        amend_doc_id: str,
        merge_mode: str,
        merged_text: str,
    ) -> dict:
        conn = None
        try:
            conn = get_db_connection()
            cur = conn.cursor()

            # ---------- load base ----------
            cur.execute(
                """
                SELECT meta_json, text_content, pdf_file_data, pdf_file_name
                FROM documents
                WHERE id = %s AND deleted_at IS NULL
                """,
                (base_doc_id,),
            )
            row = cur.fetchone()
            if not row:
                raise ValueError("Base document not found")

            base_meta_raw, _, base_pdf, base_name = row
            if isinstance(base_meta_raw, list):
                base_meta_raw = base_meta_raw[0]

            base_meta = DocumentMeta.model_validate(base_meta_raw)

            # ---------- load amend ----------
            cur.execute(
                """
                SELECT meta_json, text_content, pdf_file_data, pdf_file_name
                FROM documents
                WHERE id = %s AND deleted_at IS NULL
                """,
                (amend_doc_id,),
            )
            row = cur.fetchone()
            if not row:
                raise ValueError("Amend document not found")

            amend_meta_raw, _, amend_pdf, amend_name = row
            if isinstance(amend_meta_raw, list):
                amend_meta_raw = amend_meta_raw[0]

            amend_meta = DocumentMeta.model_validate(amend_meta_raw)

            # ---------- merge PDFs ----------
            merged_pdf = self.merge_pdf_bytes(base_pdf, amend_pdf)

            merged_file_name = (
                f"{Path(base_name).stem}"
                f"__"
                f"{Path(amend_name).stem}.pdf"
            )

            # ---------- mark base as not latest ----------
            cur.execute(
                """
                UPDATE documents
                SET is_latest = FALSE
                WHERE id = %s
                """,
                (base_doc_id,),
            )

            # ---------- create snapshot ----------
            new_doc_id = str(uuid.uuid4())

            merged_meta = DocumentMeta(
                title=base_meta.title,
                type=base_meta.type,
                announce_date=amend_meta.announce_date,
                effective_date=amend_meta.effective_date,
                version=amend_meta.version,
                is_snapshot=True,
                is_latest=True,
                related_form_id=[base_doc_id, amend_doc_id],
            )

            cur.execute(
                """
                INSERT INTO documents (
                    id,
                    type,
                    title,
                    version,
                    announce_date,
                    effective_date,
                    status,
                    pdf_file_name,
                    pdf_file_data,
                    text_content,
                    meta_json,
                    is_snapshot,
                    is_latest,
                    created_at
                )
                VALUES (%s, %s, %s, %s, %s, %s,
                        'merged', %s, %s, %s, %s,
                        TRUE, TRUE, NOW())
                """,
                (
                    new_doc_id,
                    merged_meta.type,
                    merged_meta.title,
                    merged_meta.version,
                    merged_meta.announce_date,
                    merged_meta.effective_date,
                    merged_file_name,
                    merged_pdf,
                    merged_text,
                    merged_meta.model_dump_json(ensure_ascii=False),
                ),
            )

            conn.commit()

            return {
                "id": new_doc_id,
                "file_name": merged_file_name,
                "is_snapshot": True,
                "is_latest": True,
                "related_form_id": merged_meta.related_form_id,
            }

        except Exception:
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                conn.close()
