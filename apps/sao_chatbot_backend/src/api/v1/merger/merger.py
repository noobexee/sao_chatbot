from fastapi.responses import FileResponse
from fastapi import APIRouter, HTTPException, UploadFile, File, BackgroundTasks
from pathlib import Path
import uuid
import shutil
from src.app.merger.ocr_service import run_ocr_job
from pydantic import BaseModel

class CleanTextPayload(BaseModel):
    content: str

router = APIRouter()

MOCK_DIR = Path("mock")

@router.get("/merger/doc")
def list_documents():
    if not MOCK_DIR.exists():
        return []

    docs = []
    for folder in MOCK_DIR.iterdir():
        if folder.is_dir():
            docs.append({
                "id": folder.name,
                "has_pdf": (folder / "original.pdf").exists(),
                "has_text": (folder / "text.txt").exists()
            })
    return docs

@router.get("/merger/doc/{doc_id}/original")
def get_original_pdf(doc_id: str):
    pdf_path = MOCK_DIR / doc_id / "original.pdf"

    if not pdf_path.exists():
        raise HTTPException(status_code=404, detail="PDF not found")

    return FileResponse(
        pdf_path,
        media_type="application/pdf",
        filename="original.pdf"
    )

@router.get("/merger/doc/{doc_id}/text")
def get_text(doc_id: str):
    text_path = MOCK_DIR / doc_id / "text.txt"

    if not text_path.exists():
        raise HTTPException(status_code=404, detail="Text file not found")

    return FileResponse(
        text_path,
        media_type="text/plain",
        filename="text.txt"
    )

@router.post("/doc")
def upload_new_pdf(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...)
):
    if file.content_type != "application/pdf":
        raise HTTPException(400, "Only PDF allowed")

    doc_id = str(uuid.uuid4())
    doc_dir = MOCK_DIR / doc_id
    doc_dir.mkdir(parents=True)

    pdf_path = doc_dir / "original.pdf"
    with pdf_path.open("wb") as f:
        shutil.copyfileobj(file.file, f)

    (doc_dir / "text.txt").write_text("", encoding="utf-8")
    (doc_dir / "status.txt").write_text("queued", encoding="utf-8")

    background_tasks.add_task(run_ocr_job, doc_dir)

    return {
        "id": doc_id,
        "message": "PDF uploaded. OCR processing started.",
        "status_endpoint": f"/merger/doc/{doc_id}/status",
        "text_endpoint": f"/merger/doc/{doc_id}/text"
    }

@router.get("/doc/{doc_id}/status")
def get_status(doc_id: str):
    status_path = MOCK_DIR / doc_id / "status.txt"

    if not status_path.exists():
        raise HTTPException(404, "Status not found")

    return {
        "status": status_path.read_text(encoding="utf-8")
    }

from fastapi.responses import FileResponse

@router.get("/doc/{doc_id}/text")
def get_text(doc_id: str):
    text_path = MOCK_DIR / doc_id / "text.txt"

    if not text_path.exists():
        raise HTTPException(404, "Text not found")

    return FileResponse(text_path, media_type="text/plain")

@router.post("/doc/{doc_id}/text")
def save_clean_text(doc_id: str, payload: CleanTextPayload):
    clean_path = MOCK_DIR / doc_id / "text_clean.txt"
    clean_path.write_text(payload.content, encoding="utf-8")

    return {"message": "Cleaned text saved"}