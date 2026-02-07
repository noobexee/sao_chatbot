from typing import Optional, List
from datetime import date
import uuid
import json
from src.db.connection import get_db_connection
from src.app.document.documentSchemas import DocumentMeta

class DocumentRepository:

    def save_document(
        self,
        *,
        doc_type: str,
        title: str,
        version: int,
        announce_date: date,
        effective_date: date,
        is_latest: bool,
        meta: DocumentMeta,
        main_file_name: str,
        main_file_bytes: bytes,
        related_files: Optional[List[tuple[str, bytes]]],
    ) -> dict:
        conn = None
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            doc_id = str(uuid.uuid4())

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
                    doc_type,
                    title,
                    version,
                    announce_date,
                    effective_date,
                    is_latest,
                    json.dumps(meta.model_dump(mode="json")),
                    main_file_name,
                    main_file_bytes,
                ),
            )

            related_form_id: Optional[List[str]] = None

            if related_files:
                related_form_id = []
                for filename, content in related_files:
                    file_id = str(uuid.uuid4())

                    cur.execute(
                        """
                        INSERT INTO document_files (
                            id,
                            document_id,
                            file_name,
                            file_data
                        )
                        VALUES (%s, %s, %s, %s)
                        """,
                        (file_id, doc_id, filename, content),
                    )

                    related_form_id.append(file_id)

            conn.commit()

            return {
                "id": doc_id,
                "related_form_id": related_form_id,
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
        effective_date: Optional[date],
        text_content: str,
        meta_json: list,
    ) -> None:
        conn = None
        try:
            conn = get_db_connection()
            cur = conn.cursor()

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
                    title,
                    type,
                    announce_date,
                    effective_date,
                    json.dumps(meta_json),
                    text_content,
                    doc_id,
                ),
            )

            if cur.rowcount == 0:
                raise ValueError("Document not found")

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
                    None,
                    None,
                    merged_text,
                    merged_meta.model_dump_json(ensure_ascii=False),
                ),
            )

            conn.commit()

            return new_doc_id

        except Exception:
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                conn.close()

    def bump_version_and_invalidate_latest(self, doc_type: str, title: str) -> int:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute(
            """
            SELECT COALESCE(MAX(version), 0)
            FROM documents
            WHERE type = %s AND title = %s
            """,
            (doc_type, title),
        )
        version = cur.fetchone()[0] + 1

        cur.execute(
            """
            UPDATE documents
            SET is_latest = FALSE
            WHERE type = %s AND title = %s
            """,
            (doc_type, title),
        )

        conn.commit()
        conn.close()

        return version
