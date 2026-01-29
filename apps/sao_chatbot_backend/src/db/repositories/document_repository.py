from typing import Optional, List
from datetime import date
import uuid
from src.db.connection import get_db_connection
from src.app.manager.document import DocumentMeta

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
        related_files: Optional[List[tuple[str, bytes]]],  # [(filename, bytes)]
    ) -> dict:
        conn = None
        try:
            conn = get_db_connection()
            cur = conn.cursor()

            base_meta: Optional[DocumentMeta] = None

            if previous_doc_id:
                cur.execute(
                    "SELECT meta_json FROM documents WHERE id = %s",
                    (previous_doc_id,)
                )
                row = cur.fetchone()
                if not row:
                    raise ValueError("previous document not found")

                base_meta = DocumentMeta.model_validate_json(row[0])

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
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'queued', NOW())
                """,
                (
                    doc_id,
                    safe_type,
                    derived_title,
                    version,
                    announce_date,
                    effective_date,
                    True,
                    meta.model_dump_json(ensure_ascii=False),
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

        except Exception as e:
            if conn:
                conn.rollback()
            raise e
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
                meta = DocumentMeta.model_validate_json(meta_json)

                docs.append({
                    "id": doc_id,
                    **meta.model_dump(),
                    "status": status,
                })

            cur.close()
            return docs

        except Exception as e:
            raise e
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

            file_name, file_data = row

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
                """
                SELECT meta_json
                FROM documents
                WHERE id = %s
                """,
                (doc_id,),
            )
            row = cur.fetchone()
            if not row:
                raise ValueError("Document not found")

            meta = DocumentMeta.model_validate_json(row[0])
            meta.title = title.strip()
            meta.type = type.strip().lower().replace(" ", "_")
            meta.announce_date = announce_date
            meta.effective_date = effective_date
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
                    meta.title,
                    meta.type,
                    meta.announce_date,
                    meta.effective_date,
                    meta.model_dump_json(ensure_ascii=False),
                    text_content,
                    doc_id,
                ),
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

            text_content = row[0]
            if text_content is None:
                raise ValueError("Text not found")

            return text_content

        finally:
            if conn:
                conn.close()
                
    def get_metadata(self, doc_id: str) -> DocumentMeta:
        conn = None
        try:
            conn = get_db_connection()
            cur = conn.cursor()

            cur.execute(
                """
                SELECT meta_json
                FROM documents
                WHERE id = %s
                """,
                (doc_id,),
            )

            row = cur.fetchone()
            if not row:
                raise ValueError("Document not found")

            return DocumentMeta.model_validate_json(row[0])

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