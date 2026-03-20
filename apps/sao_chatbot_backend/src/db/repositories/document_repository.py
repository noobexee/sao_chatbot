from typing import Optional, List
import uuid
import base64
from src.db.connection import get_db_connection
from src.app.document.documentSchemas import DocumentMeta, MergeRequest


class DocumentRepository:

    # CREATE
    def save_document(
        self,
        *,
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
                    is_snapshot,
                    pdf_file_name,
                    pdf_file_data,
                    status,
                    created_at
                )
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'processing',NOW())
                """,
                (
                    doc_id,
                    meta.type,
                    meta.title,
                    meta.version,
                    meta.announce_date,
                    meta.effective_date,
                    meta.is_latest,
                    meta.is_snapshot,
                    main_file_name,
                    main_file_bytes,
                ),
            )

            related_form_id = []
            if related_files:
                for filename, content in related_files:
                    file_id = str(uuid.uuid4())
                    cur.execute(
                        """
                        INSERT INTO document_files (id, document_id, file_name, file_data)
                        VALUES (%s,%s,%s,%s)
                        """,
                        (file_id, doc_id, filename, content),
                    )
                    related_form_id.append(file_id)

            conn.commit()
            return {"id": doc_id, "related_form_id": related_form_id or None}

        except Exception:
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                conn.close()


    # LIST
    def list_documents(self) -> List[dict]:
        conn = get_db_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT
                    id,
                    title,
                    type,
                    announce_date,
                    effective_date,
                    version,
                    is_snapshot,
                    is_latest,
                    status
                FROM documents
                ORDER BY created_at DESC
                """
            )

            result = []
            for r in cur.fetchall():
                result.append({
                    "id": r[0],
                    "title": r[1],
                    "type": r[2],
                    "announce_date": r[3],
                    "effective_date": r[4],
                    "version": r[5],
                    "is_snapshot": r[6],
                    "is_latest": r[7],
                    "status": r[8],
                })

            return result
        finally:
            conn.close()

    # GET ORIGINAL PDF
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
            if not row or not row[1]:
                raise ValueError("PDF not found")

            return row[0], row[1]

        finally:
            if conn:
                conn.close()

    # STATUS
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
                if current_page and total_pages:
                    response.update({
                        "current_page": current_page,
                        "total_pages": total_pages,
                    })

            if status == "done" and pages:
                response["pages"] = pages

            return response

        finally:
            if conn:
                conn.close()

    # METADATA
    def get_metadata(self, doc_id: str) -> DocumentMeta:
        conn = get_db_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT
                    title,
                    type,
                    announce_date,
                    effective_date,
                    version,
                    is_snapshot,
                    is_latest
                FROM documents
                WHERE id = %s
                """,
                (doc_id,),
            )

            row = cur.fetchone()
            if not row:
                raise ValueError("Document not found")

            return DocumentMeta(
                title=row[0],
                type=row[1],
                announce_date=row[2],
                effective_date=row[3],
                version=row[4],
                is_snapshot=row[5],
                is_latest=row[6],
            )
        finally:
            conn.close()

    # EDIT
    def edit_doc(
        self,
        *,
        doc_id: str,
        meta: DocumentMeta,
        text_content: str,
    ) -> None:
        conn = get_db_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                """
                UPDATE documents
                SET
                    title = %s,
                    type = %s,
                    announce_date = %s,
                    effective_date = %s,
                    version = %s,
                    is_latest = %s,
                    is_snapshot = %s,
                    text_content = %s,
                    updated_at = NOW()
                WHERE id = %s
                """,
                (
                    meta.title,
                    meta.type,
                    meta.announce_date,
                    meta.effective_date,
                    meta.version,
                    meta.is_latest,
                    meta.is_snapshot,
                    text_content,
                    doc_id,
                ),
            )

            if cur.rowcount == 0:
                raise ValueError("Document not found")

            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()


    # TEXT
    def get_text(self, doc_id: str) -> str:
        conn = None
        try:
            conn = get_db_connection()
            cur = conn.cursor()

            cur.execute(
                "SELECT text_content FROM documents WHERE id = %s",
                (doc_id,),
            )

            row = cur.fetchone()
            if not row or row[0] is None:
                raise ValueError("Text not ready")

            return row[0]

        finally:
            if conn:
                conn.close()

    # DELETE
    def delete_document(self, doc_id: str) -> None:
        conn = None
        try:
            conn = get_db_connection()
            cur = conn.cursor()

            cur.execute("DELETE FROM document_files WHERE document_id = %s", (doc_id,))
            cur.execute("DELETE FROM documents WHERE id = %s", (doc_id,))

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

    def merge_documents(
        self,
        *,
        payload: MergeRequest,
        merged_text: str,
    ) -> str:

        conn = get_db_connection()
        try:
            cur = conn.cursor()

            cur.execute(
                """
                UPDATE documents
                SET is_latest = FALSE
                WHERE id = %s
                """,
                (payload.amend_doc_id,),
            )

            new_doc_id = str(uuid.uuid4())

            is_snapshot = payload.merge_mode != "replace_all"

            if payload.merge_mode == "replace_all":
                query = """
                    INSERT INTO documents (
                        id,
                        type,
                        title,
                        announce_date,
                        effective_date,
                        version,
                        text_content,
                        status,
                        is_snapshot,
                        is_latest,
                        pdf_file_name,
                        pdf_file_data,
                        created_at
                    )
                    SELECT
                        %s,
                        type,
                        title,
                        announce_date,
                        effective_date,
                        version,
                        %s,
                        'merged',
                        FALSE,
                        TRUE,
                        pdf_file_name,
                        pdf_file_data,
                        NOW()
                    FROM documents
                    WHERE id = %s
                """
            else:
                query = """
                    INSERT INTO documents (
                        id,
                        type,
                        title,
                        announce_date,
                        effective_date,
                        version,
                        text_content,
                        status,
                        is_snapshot,
                        is_latest,
                        created_at
                    )
                    SELECT
                        %s,
                        type,
                        title,
                        announce_date,
                        effective_date,
                        version,
                        %s,
                        'merged',
                        TRUE,
                        TRUE,
                        NOW()
                    FROM documents
                    WHERE id = %s
                """

            cur.execute(
                query,
                (new_doc_id, merged_text, payload.amend_doc_id),
            )

            if is_snapshot:

                def expand_sources(doc_id: str):

                    cur.execute(
                        """
                        SELECT is_snapshot, version
                        FROM documents
                        WHERE id = %s
                        """,
                        (doc_id,),
                    )

                    row = cur.fetchone()
                    if not row:
                        raise ValueError("Document not found")

                    is_snap, version = row

                    # normal document
                    if not is_snap:
                        if version is None or version <= 0:
                            raise ValueError("Invalid document version")
                        return [(doc_id, version)]

                    # snapshot → flatten
                    cur.execute(
                        """
                        SELECT source_id
                        FROM document_snapshot_versions
                        WHERE snapshot_id = %s
                        ORDER BY version_order
                        """,
                        (doc_id,),
                    )

                    source_ids = [r[0] for r in cur.fetchall()]
                    if not source_ids:
                        raise ValueError("Snapshot has no lineage")

                    cur.execute(
                        """
                        SELECT id, version
                        FROM documents
                        WHERE id = ANY(%s)
                        """,
                        (source_ids,),
                    )

                    version_map = {r[0]: r[1] for r in cur.fetchall()}

                    return [(sid, version_map[sid]) for sid in source_ids]

                base_sources = expand_sources(payload.base_doc_id)
                amend_sources = expand_sources(payload.amend_doc_id)

                final_sources = base_sources + amend_sources

                insert_rows = []
                order = 1

                for sid, ver in final_sources:
                    insert_rows.append((new_doc_id, sid, order))
                    order += 1

                cur.executemany(
                    """
                    INSERT INTO document_snapshot_versions
                    (snapshot_id, source_id, version_order)
                    VALUES (%s, %s, %s)
                    """,
                    insert_rows,
                )

            conn.commit()
            return new_doc_id

        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _resolve_sources(self, cur, doc_id: str):

        cur.execute(
            """
            SELECT is_snapshot, version
            FROM documents
            WHERE id = %s
            """,
            (doc_id,),
        )

        row = cur.fetchone()
        if not row:
            raise ValueError("Document not found")

        is_snapshot, version = row

        if not is_snapshot:
            return [(doc_id, version)]

        cur.execute(
            """
            SELECT source_id
            FROM document_snapshot_versions
            WHERE snapshot_id = %s
            ORDER BY version_order
            """,
            (doc_id,),
        )

        source_ids = [r[0] for r in cur.fetchall()]

        if not source_ids:
            raise ValueError("Snapshot has no lineage")

        cur.execute(
            """
            SELECT id, version
            FROM documents
            WHERE id = ANY(%s)
            """,
            (source_ids,),
        )

        version_map = {r[0]: r[1] for r in cur.fetchall()}

        return [(sid, version_map[sid]) for sid in source_ids]

    def get_snapshot_sources(self, snapshot_id: str):
        conn = get_db_connection()
        try:
            cur = conn.cursor()

            cur.execute(
                """
                SELECT source_id, version_order
                FROM document_snapshot_versions
                WHERE snapshot_id = %s
                ORDER BY version_order
                """,
                (snapshot_id,),
            )

            rows = cur.fetchall()

            return [
                {
                    "source_id": r[0],
                    "order": r[1]
                }
                for r in rows
            ]

        finally:
            conn.close()

    # VERSION BUMP
    def bump_version_and_invalidate_latest(self, doc_id: str):
        conn = get_db_connection()
        cur = conn.cursor()

        try:

            cur.execute(
                """
                SELECT type, title, version
                FROM documents
                WHERE id = %s
                """,
                (doc_id,),
            )
            row = cur.fetchone()
            if not row:
                return None

            doc_type, title, version = row

            cur.execute(
                """
                UPDATE documents
                SET
                    is_latest = FALSE,
                    status = 'need_attention'
                WHERE id = %s
                """,
                (doc_id,),
            )

            conn.commit()
            return doc_type, title, version

        except Exception:
            conn.rollback()
            return None

        finally:
            conn.close()
    
    def mark_done(self, doc_id: str):
        conn = None
        try:
            conn = get_db_connection()
            cur = conn.cursor()

            cur.execute(
                """
                UPDATE documents
                SET status = 'done',
                    updated_at = NOW()
                WHERE id = %s
                """,
                (doc_id,),
            )

            conn.commit()

        finally:
            if conn:
                conn.close()

    def get_related_doc(self, document_id: str) -> List[dict]:
        conn = get_db_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT
                    id,
                    document_id,
                    file_name,
                    file_data,
                    created_at
                FROM document_files
                WHERE document_id = %s
                ORDER BY created_at DESC
                """,
                (document_id,)
            )

            result = []
            for r in cur.fetchall():
                result.append({
                    "id": r[0],
                    "document_id": r[1],
                    "file_name": r[2],
                    "file_data": base64.b64encode(r[3]).decode("utf-8"),
                })

            return result
        finally:
            conn.close()