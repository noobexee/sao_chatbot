from fastapi.responses import FileResponse, Response
from fastapi import APIRouter, HTTPException, UploadFile, File, BackgroundTasks, Form
from pathlib import Path
import shutil
from typing import Optional, List
from datetime import datetime, date
import json
from src.app.service.ocr_service import run_ocr_job
from src.app.manager.document import DocumentMeta
from src.db.repositories.document_repository import DocumentRepository

router = APIRouter()
MOCK_DIR = Path("mock")

def parse_date(value: Optional[str]) -> Optional[date]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value).date()
    except ValueError:
        try:
            return datetime.strptime(value, "%d-%m-%Y").date()
        except ValueError:
            raise HTTPException(400, f"Invalid date format: {value}")

def derive_title(file: UploadFile, title: Optional[str]) -> str:
    if title and title.strip():
        return title.strip()
    return Path(file.filename).stem

def find_doc_dir_by_id(doc_id: str) -> Optional[Path]:
    if not MOCK_DIR.exists():
        return None
    for type_dir in MOCK_DIR.iterdir():
        candidate = type_dir / doc_id
        if candidate.is_dir():
            return candidate
    return None

def load_meta(meta_path: Path) -> DocumentMeta:
    return DocumentMeta.parse_obj(
        json.loads(meta_path.read_text(encoding="utf-8"))
    )

def get_next_version(doc_type: str, title: str) -> int:
    type_dir = MOCK_DIR / doc_type
    if not type_dir.exists():
        return 1
    max_version = 0
    for doc_dir in type_dir.iterdir():
        meta_path = doc_dir / "meta.json"
        if not meta_path.exists():
            continue
        meta = load_meta(meta_path)
        if meta.title == title and meta.version:
            max_version = max(max_version, meta.version)

    return max_version + 1 if max_version else 1


def mark_previous_not_latest(doc_type: str, title: str):
    type_dir = MOCK_DIR / doc_type
    if not type_dir.exists():
        return

    for doc_dir in type_dir.iterdir():
        meta_path = doc_dir / "meta.json"
        if not meta_path.exists():
            continue

        meta = load_meta(meta_path)
        if meta.title == title and meta.is_latest:
            meta.is_latest = False
            meta_path.write_text(
                meta.model_dump_json(ensure_ascii=False, indent=2),
                encoding="utf-8"
            )

@router.get("/doc")
def list_documents():
    repo = DocumentRepository()
    return repo.list_documents()

@router.get("/doc/{doc_id}/original")
def get_original_pdf(doc_id: str):
    repo = DocumentRepository()

    try:
        file_name, pdf_bytes = repo.get_original_pdf(doc_id)
    except ValueError as e:
        raise HTTPException(404, str(e))

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'inline; filename="{file_name}"'
        },
    )


@router.post("/doc")
def upload_new_pdf(
    background_tasks: BackgroundTasks,
    doc_type: str = Form(...),
    title: Optional[str] = Form(None),
    announce_date: date = Form(...),
    effective_date: date = Form(...),
    is_first_version: bool = Form(...),
    previous_doc_id: Optional[str] = Form(None),
    main_file: UploadFile = File(...),
    related_files: Optional[List[UploadFile]] = File(None),
):
    if not main_file.content_type or "pdf" not in main_file.content_type.lower():
        raise HTTPException(400, "main_file must be a PDF")

    repo = DocumentRepository()

    result = repo.save_pdf(
        doc_type=doc_type,
        title=title,
        announce_date=announce_date,
        effective_date=effective_date,
        is_first_version=is_first_version,
        previous_doc_id=previous_doc_id,
        main_file_name=main_file.filename,
        main_file_bytes=main_file.file.read(),
        related_files=[
            (rf.filename, rf.file.read()) for rf in related_files
        ] if related_files else None,
    )

    background_tasks.add_task(run_ocr_job, result["id"])

    return result

@router.get("/doc/{doc_id}/status")
def get_status(doc_id: str):
    repo = DocumentRepository()
    try:
        return repo.get_status(doc_id)
    except ValueError as e:
        raise HTTPException(404, str(e))


@router.put("/doc/{doc_id}/edit")
def edit_doc(
    doc_id: str,
    title: str = Form(...),
    type: str = Form(...),
    announce_date: str = Form(...),
    effective_date: Optional[str] = Form(None),
    file: UploadFile = File(...),
):
    if file.content_type != "text/plain":
        raise HTTPException(400, "Only .txt allowed")

    try:
        text_content = file.file.read().decode("utf-8")
    except Exception:
        raise HTTPException(400, "Invalid text file")

    repo = DocumentRepository()

    try:
        repo.edit_doc(
            doc_id=doc_id,
            title=title,
            type=type,
            announce_date=parse_date(announce_date),
            effective_date=parse_date(effective_date) if effective_date else None,
            text_content=text_content,
        )
    except ValueError as e:
        raise HTTPException(404, str(e))

    return {
        "status": "updated",
        "doc_id": doc_id,
    }

@router.get("/doc/{doc_id}/text")
def get_text(doc_id: str):
    repo = DocumentRepository()
    try:
        text = repo.get_text(doc_id)
    except ValueError as e:
        raise HTTPException(404, str(e))

    return Response(
        content=text,
        media_type="text/plain; charset=utf-8",
    )


@router.get("/doc/{doc_id}/meta", response_model=DocumentMeta)
def get_metadata(doc_id: str):
    repo = DocumentRepository()
    try:
        return repo.get_metadata(doc_id)
    except ValueError as e:
        raise HTTPException(404, str(e))

@router.delete("/doc/{doc_id}")
def delete_document(doc_id: str):
    repo = DocumentRepository()

    try:
        repo.delete_document(doc_id)
    except ValueError as e:
        raise HTTPException(404, str(e))

    return {
        "status": "deleted",
        "doc_id": doc_id,
    }
