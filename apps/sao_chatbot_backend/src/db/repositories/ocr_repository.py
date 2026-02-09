from src.db.connection import get_db_connection
class OCRRepository:

    def mark_processing(self, doc_id: str):
        conn = None
        try:
            conn = get_db_connection()
            cur = conn.cursor()

            cur.execute(
                """
                UPDATE documents
                SET status = 'processing',
                    current_page = 0,
                    updated_at = NOW()
                WHERE id = %s
                """,
                (doc_id,),
            )

            conn.commit()

        finally:
            if conn:
                conn.close()

    def update_progress(self, doc_id: str, current: int, total: int):
        conn = None
        try:
            conn = get_db_connection()
            cur = conn.cursor()

            cur.execute(
                """
                UPDATE documents
                SET current_page = %s,
                    total_pages = %s,
                    updated_at = NOW()
                WHERE id = %s
                """,
                (current, total, doc_id),
            )

            conn.commit()

        finally:
            if conn:
                conn.close()

    def save_ocr_result(self, doc_id: str, text: str, pages: int):
        conn = None
        try:
            conn = get_db_connection()
            cur = conn.cursor()

            cur.execute(
                """
                UPDATE documents
                SET status = 'done',
                    text_content = %s,
                    pages = %s,
                    current_page = %s,
                    updated_at = NOW()
                WHERE id = %s
                """,
                (text, pages, pages, doc_id),
            )

            conn.commit()

        finally:
            if conn:
                conn.close()

    def mark_failed(self, doc_id: str):
        conn = None
        try:
            conn = get_db_connection()
            cur = conn.cursor()

            cur.execute(
                """
                UPDATE documents
                SET status = 'failed',
                    updated_at = NOW()
                WHERE id = %s
                """,
                (doc_id,),
            )

            conn.commit()

        finally:
            if conn:
                conn.close()


