from pathlib import Path
from src.app.llm_base.ocr import TyphoonOCRLoader
from typing import List
from langchain_core.documents import Document

def typhoon_docs_to_text(docs: List[Document]) -> str:
    pages = []

    for doc in docs:
        page = doc.metadata.get("page", "?")
        content = doc.page_content.strip()

        if content:
            pages.append(f"\n\n--- Page {page} ---\n{content}")

    return "\n".join(pages)

def write_status(doc_dir: Path, status: str):
    (doc_dir / "status.txt").write_text(status, encoding="utf-8")

def run_ocr_job(doc_dir: Path):
    text_path = doc_dir / "text.txt"
    pdf_path = doc_dir / "original.pdf"
    pages_path = doc_dir / "pages.txt"

    def progress_cb(current: int, total: int):
        write_status(doc_dir, f"processing:page={current}/{total}")

    try:
        write_status(doc_dir, "processing")

        loader = TyphoonOCRLoader(
            file_path=str(pdf_path),
            progress_cb=progress_cb
        )

        documents = loader.load()
        if not documents:
            raise RuntimeError("OCR returned no content")

        text_path.write_text(
            typhoon_docs_to_text(documents),
            encoding="utf-8"
        )

        pages_path.write_text(str(len(documents)), encoding="utf-8")
        write_status(doc_dir, "done")

    except Exception as e:
        write_status(doc_dir, "error")
        text_path.write_text(f"OCR failed: {str(e)}", encoding="utf-8")

