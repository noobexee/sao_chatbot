from pathlib import Path
import tempfile
import shutil
from src.db.repositories.ocr_repository import OCRRepository
from src.app.llm.ocr import TyphoonOCRLoader
from langchain_core.documents import Document


def typhoon_docs_to_text(docs: list[Document]) -> str:
    pages = []

    for doc in docs:
        page = doc.metadata.get("page", "?")
        content = doc.page_content.strip()

        if content:
            pages.append(f"\n\n--- Page {page} ---\n{content}")

    return "\n".join(pages)


def run_ocr_and_update_db(doc_id: str, pdf_bytes: bytes):
    repo = OCRRepository()

    try:
        repo.mark_processing(doc_id)

        work_dir = Path(tempfile.mkdtemp(prefix="ocr_"))
        pdf_path = work_dir / "input.pdf"
        pdf_path.write_bytes(pdf_bytes)

        def progress_cb(current: int, total: int):
            repo.update_progress(
                doc_id=doc_id,
                current=current,
                total=total,
            )
        loader = TyphoonOCRLoader(
            file_path=str(pdf_path),
            progress_cb=progress_cb,
        )

        documents = loader.load()
        if not documents:
            raise RuntimeError("OCR returned no content")

        text_content = typhoon_docs_to_text(documents)
        pages = len(documents)

        repo.save_ocr_result(
            doc_id=doc_id,
            text=text_content,
            pages=pages,
        )

    except Exception:
        repo.mark_failed(doc_id)
        raise

    finally:
        shutil.rmtree(work_dir, ignore_errors=True)
