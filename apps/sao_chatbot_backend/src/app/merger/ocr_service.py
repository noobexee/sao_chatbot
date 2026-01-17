from pathlib import Path
from src.app.llm.ocr import TyphoonOCRLoader
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


def run_ocr_job(doc_dir: Path):
    pdf_path = doc_dir / "original.pdf"
    text_path = doc_dir / "text.txt"
    status_path = doc_dir / "status.txt"

    try:
        status_path.write_text("processing", encoding="utf-8")

        loader = TyphoonOCRLoader(str(pdf_path))
        documents = loader.load()

        full_text = typhoon_docs_to_text(documents)
        text_path.write_text(full_text, encoding="utf-8")

        status_path.write_text("done", encoding="utf-8")

    except Exception as e:
        status_path.write_text(f"error: {str(e)}", encoding="utf-8")
