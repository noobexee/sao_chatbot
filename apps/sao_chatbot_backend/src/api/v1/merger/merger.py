from fastapi.responses import FileResponse
from fastapi import APIRouter, HTTPException, UploadFile, File, BackgroundTasks, Form
from pathlib import Path
import uuid
import shutil
from src.app.merger.ocr_service import run_ocr_job
from pydantic import BaseModel
from typing import Optional
from datetime import date
import json

class DocumentMeta(BaseModel):
    title: str
    pdf_name: str
    valid_from: Optional[date] = None
    valid_until: Optional[date] = None
    version: Optional[str] = None

def find_doc_dir_by_id(doc_id: str) -> Optional[Path]:
    if not MOCK_DIR.exists():
        return None

    for type_dir in MOCK_DIR.iterdir():
        if not type_dir.is_dir():
            continue

        candidate = type_dir / doc_id
        if candidate.exists() and candidate.is_dir():
            return candidate

    return None

router = APIRouter()
MOCK_DIR = Path("mock")

@router.get("/merger/doc")
def list_documents():
    if not MOCK_DIR.exists():
        return []
    docs = []
    for type_dir in MOCK_DIR.iterdir():
        if not type_dir.is_dir():
            continue
        doc_type = type_dir.name
        for doc_dir in type_dir.iterdir():
            if not doc_dir.is_dir():
                continue
            meta_path = doc_dir / "meta.json"
            meta = (
                json.loads(meta_path.read_text(encoding="utf-8"))
                if meta_path.exists()
                else {}
            )
            docs.append({
                "type": doc_type,
                "id": doc_dir.name,
                "title": meta.get("title"),
                "version": meta.get("version"),
                "valid_from": meta.get("valid_from"),
                "valid_until": meta.get("valid_until"),
                "has_pdf": (doc_dir / "original.pdf").exists(),
                "has_text": (doc_dir / "text.txt").exists(),
                "status": (
                    (doc_dir / "status.txt").read_text(encoding="utf-8")
                    if (doc_dir / "status.txt").exists()
                    else "unknown"
                )
            })
    return docs


@router.get("/merger/doc/{doc_id}/original")
def get_original_pdf(doc_id: str):
    if not MOCK_DIR.exists():
        raise HTTPException(404, "Storage not found")
    pdf_path = None
    for type_dir in MOCK_DIR.iterdir():
        if not type_dir.is_dir():
            continue
        candidate = type_dir / doc_id / "original.pdf"
        if candidate.exists():
            pdf_path = candidate
            break
    if not pdf_path:
        raise HTTPException(404, "PDF not found")
    return FileResponse(
        pdf_path,
        media_type="application/pdf",
        filename="original.pdf"
    )

@router.post("/doc")
def upload_new_pdf(
    background_tasks: BackgroundTasks,
    type: str = Form(...),
    title: str = Form(...),
    version: str = Form(None),
    valid_from: str = Form(None),
    valid_until: str = Form(None),
    file: UploadFile = File(...)
):
    if file.content_type != "application/pdf":
        raise HTTPException(400, "Only PDF allowed")
    safe_type = type.strip().lower().replace(" ", "_")
    doc_id = str(uuid.uuid4())
    doc_dir = MOCK_DIR / safe_type / doc_id
    doc_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = doc_dir / "original.pdf"
    with pdf_path.open("wb") as f:
        shutil.copyfileobj(file.file, f)
    meta = {
        "id": doc_id,
        "type": safe_type,
        "title": title,
        "pdf_name": file.filename,
        "version": version,
        "valid_from": valid_from,
        "valid_until": valid_until
    }
    (doc_dir / "meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    (doc_dir / "text.txt").write_text("", encoding="utf-8")
    (doc_dir / "status.txt").write_text("queued", encoding="utf-8")
    background_tasks.add_task(run_ocr_job, doc_dir)
    return {
        "id": doc_id,
        "type": safe_type,
        "title": title,
        "version": version,
        "message": "PDF uploaded. OCR processing started.",
        "status_endpoint": f"/merger/doc/{safe_type}/{doc_id}/status",
        "text_endpoint": f"/merger/doc/{safe_type}/{doc_id}/text"
    }

@router.get("/doc/{doc_id}/status")
def get_status(doc_id: str):
    doc_dir = find_doc_dir_by_id(doc_id)
    if not doc_dir:
        raise HTTPException(404, "Document not found")
    status_path = doc_dir / "status.txt"
    if not status_path.exists():
        raise HTTPException(404, "Status not found")
    return {"status": status_path.read_text(encoding="utf-8")}

@router.get("/doc/{doc_id}/text")
def get_text(doc_id: str):
    doc_dir = find_doc_dir_by_id(doc_id)
    if not doc_dir:
        raise HTTPException(404, "Document not found")
    text_path = doc_dir / "text.txt"
    if not text_path.exists():
        raise HTTPException(404, "Text not found")
    return FileResponse(text_path, media_type="text/plain")

@router.post("/doc/{doc_id}/text")
def save_clean_text(
    doc_id: str,
    file: UploadFile = File(...)
):
    doc_dir = find_doc_dir_by_id(doc_id)
    if not doc_dir:
        raise HTTPException(404, "Document not found")
    if file.content_type not in ["text/plain"]:
        raise HTTPException(400, "Only .txt files are allowed")
    text_path = doc_dir / "text.txt"
    content = file.file.read().decode("utf-8")
    text_path.write_text(content, encoding="utf-8")
    return {
        "message": "Cleaned text uploaded and saved",
        "doc_id": doc_id
    }

@router.get("/doc/{doc_id}/meta")
def get_metadata(doc_id: str):
    doc_dir = find_doc_dir_by_id(doc_id)
    if not doc_dir:
        raise HTTPException(404, "Document not found")
    meta_path = doc_dir / "meta.json"
    if not meta_path.exists():
        raise HTTPException(404, "Metadata not found")
    return json.loads(meta_path.read_text(encoding="utf-8"))
