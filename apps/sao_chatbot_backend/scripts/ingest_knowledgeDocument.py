import os
import csv
import uuid
import psycopg2
from datetime import datetime, date
from dotenv import load_dotenv
import unicodedata
import hashlib

from src.app.document.documentSchemas import DocumentMeta
from src.app.document.documentUpdate import DocumentUpdater

load_dotenv()


def convert_thai_date(date_str: str) -> date:
    if not date_str:
        return None
    d = datetime.strptime(date_str, "%d/%m/%Y")
    return date(d.year, d.month, d.day)


def read_binary_file(file_path: str):
    try:
        with open(file_path, "rb") as f:
            return f.read()
    except Exception:
        print(f"⚠️ Missing PDF: {file_path}")
        return None


def read_text_file(file_path: str):
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception:
        print(f"⚠️ Missing TXT: {file_path}")
        return None


def normalize_text(s: str) -> str:
    return unicodedata.normalize("NFC", s.strip())


def hash_content(text):
    if text is None:
        return None
    return hashlib.md5(text.encode("utf-8")).hexdigest()


def import_documents():
    db_url = os.getenv("SQL_DATABASE_URL")

    if not db_url:
        print("Error: SQL_DATABASE_URL is missing from .env")
        return

    CSV_PATH = "storage/knowledgebase.csv"
    FILE_BASE_DIR = "storage/files"

    updater = DocumentUpdater()

    try:
        conn = psycopg2.connect(db_url)
        cur = conn.cursor()

        with open(CSV_PATH, newline='', encoding="utf-8-sig") as csvfile:
            reader = csv.DictReader(csvfile)

            print("Headers:", reader.fieldnames)

            for row in reader:
                try:

                    meta = DocumentMeta(
                        title=row["title"],
                        type=row["type"],
                        version=int(row["version"]),
                        announce_date=convert_thai_date(row["announce_date"]),
                        effective_date=convert_thai_date(row["effective_date"]),
                        is_latest=row["is_latest"].upper() == "TRUE",
                        is_snapshot=row["is_snapshot"].upper() == "TRUE",
                        related_form_id=None
                    )

                    status = row["status"]

                    base_name = row["pdf_file_path"].strip()

                    pdf_filename = base_name + ".pdf"
                    txt_filename = base_name + ".txt"

                    pdf_path = os.path.join(FILE_BASE_DIR, pdf_filename)
                    txt_path = os.path.join(FILE_BASE_DIR, txt_filename)

                    if not os.path.exists(pdf_path):
                        print(f"❌ PDF not found: {pdf_filename}")
                        continue

                    pdf_bytes = read_binary_file(pdf_path)
                    text_content = read_text_file(txt_path)

                    new_hash = hash_content(text_content)

                    # --- check existing ---
                    cur.execute(
                        """
                        SELECT id, text_content
                        FROM documents
                        WHERE title=%s AND version=%s
                        """,
                        (meta.title, meta.version)
                    )

                    existing = cur.fetchone()

                    # CASE 1: document exists
                    if existing:
                        doc_id, old_text = existing
                        old_hash = hash_content(old_text)

                        if old_hash == new_hash:
                            print(f"⏭️ Skipped (unchanged): {meta.title} v{meta.version}")
                            continue

                        # update
                        cur.execute("""
                            UPDATE documents
                            SET
                                pdf_file_name=%s,
                                pdf_file_data=%s,
                                text_content=%s,
                                status=%s,
                                updated_at=NOW()
                            WHERE id=%s
                        """, (
                            pdf_filename,
                            psycopg2.Binary(pdf_bytes),
                            text_content,
                            status,
                            doc_id
                        ))

                        conn.commit()

                        updater.new_document(
                            doc_data=meta,
                            doc_id=doc_id,
                            text=text_content
                        )

                        print(f"🔄 Updated: {meta.title} v{meta.version}")
                        continue

                    # CASE 2: new document
                    doc_id = str(uuid.uuid4())

                    cur.execute("""
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
                            text_content,
                            status,
                            created_at,
                            updated_at
                        )
                        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,NOW(),NOW())
                    """, (
                        doc_id,
                        meta.type,
                        meta.title,
                        meta.version,
                        meta.announce_date,
                        meta.effective_date,
                        meta.is_latest,
                        meta.is_snapshot,
                        pdf_filename,
                        psycopg2.Binary(pdf_bytes),
                        text_content,
                        status,
                    ))

                    conn.commit()
                    
                    updater.new_document(
                        doc_data=meta,
                        doc_id=doc_id,
                        text=text_content
                    )

                    print(f"✅ Inserted: {meta.title} v{meta.version}")

                except Exception as row_err:
                    conn.rollback()
                    print(f"❌ Row failed: {row.get('title')} → {row_err}")

        print("\n🎉 Import completed!")

    except Exception as e:
        print(f"Database Error: {e}")

    finally:
        if 'conn' in locals() and conn:
            cur.close()
            conn.close()


if __name__ == "__main__":
    import_documents()