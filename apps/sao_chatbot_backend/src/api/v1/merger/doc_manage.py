from fastapi.responses import FileResponse
from fastapi import APIRouter, HTTPException, UploadFile, File, BackgroundTasks, Form
from pathlib import Path
import uuid
import shutil
from src.app.service.ocr_service import run_ocr_job
from typing import Optional
from datetime import datetime, date
import json
from src.api.v1.models.documnet import DocumentMeta

router = APIRouter()
MOCK_DIR = Path("mock")

def parse_date(value: Optional[str]) -> Optional[date]:
    if not value:
        return None
    try:
        # ISO: YYYY-MM-DD
        return datetime.fromisoformat(value).date()
    except ValueError:
        try:
            # DD-MM-YYYY
            return datetime.strptime(value, "%d-%m-%Y").date()
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid date format: {value}"
            )

def derive_title(file: UploadFile, title: str | None) -> str:
    if title and title.strip():
        return title.strip()
    return Path(file.filename).stem

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

def load_meta(meta_path: Path) -> DocumentMeta:
    return DocumentMeta.parse_obj(
        json.loads(meta_path.read_text(encoding="utf-8"))
    )

@router.get("/doc")
def list_documents():
    docs = []
    if not MOCK_DIR.exists():
        return docs
    for type_dir in MOCK_DIR.iterdir():
        for doc_dir in type_dir.iterdir():
            meta_path = doc_dir / "meta.json"
            if not meta_path.exists():
                continue
            meta = load_meta(meta_path)
            docs.append({
                "id": doc_dir.name,
                **meta.dict(),
                "status": (doc_dir / "status.txt").read_text().strip()
            })
    return docs


@router.get("/doc/{doc_id}/original")
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
    title: str | None = Form(None),
    version: str | None = Form(None),
    valid_from: date = Form(...),    
    valid_until: date | None = Form(None),
    file: UploadFile = File(...)
):
    if file.content_type != "application/pdf":
        raise HTTPException(400, "Only PDF allowed")
    safe_type = type.strip().lower().replace(" ", "_")
    doc_id = str(uuid.uuid4())
    doc_dir = MOCK_DIR / safe_type / doc_id
    doc_dir.mkdir(parents=True, exist_ok=True)
    with (doc_dir / "original.pdf").open("wb") as f:
        shutil.copyfileobj(file.file, f)
    meta = DocumentMeta(
        title=derive_title(file, title),
        type=safe_type,
        valid_from=valid_from,
        valid_until=valid_until,
        version=version,
        is_snapshot=False,
        got_updated=False,
        is_first_version=True
    )
    (doc_dir / "meta.json").write_text(
    meta.model_dump_json(ensure_ascii=False, indent=2),
    encoding="utf-8",
    )
    (doc_dir / "text.txt").write_text("", encoding="utf-8")
    (doc_dir / "status.txt").write_text("queued", encoding="utf-8")
    background_tasks.add_task(run_ocr_job, doc_dir)
    return {
        "id": doc_id,
        "type": safe_type,
        "title": meta.title,
        "version": meta.version,
        "is_snapshot": False
    }

@router.get("/doc/{doc_id}/status")
def get_status(doc_id: str):
    doc_dir = find_doc_dir_by_id(doc_id)
    if not doc_dir:
        raise HTTPException(404, "Document not found")
    status_path = doc_dir / "status.txt"
    if not status_path.exists():
        raise HTTPException(404, "Status not found")
    raw_status = status_path.read_text(encoding="utf-8").strip()
    response = {
        "status": raw_status
    }
    if raw_status.startswith("processing:page="):
        try:
            _, value = raw_status.split("=", 1)
            current, total = value.split("/", 1)
            response = {
                "status": "processing",
                "current_page": int(current),
                "total_pages": int(total),
                "message": f"Processing Page {current}/{total}"
            }
        except Exception:
            response = {"status": "processing"}
    elif raw_status == "done":
        pages_path = doc_dir / "pages.txt"
        if pages_path.exists():
            try:
                response["pages"] = int(pages_path.read_text().strip())
            except Exception:
                pass

    return response

@router.get("/doc/{doc_id}/text")
def get_text(doc_id: str):
    doc_dir = find_doc_dir_by_id(doc_id)
    if not doc_dir:
        raise HTTPException(404, "Document not found")
    text_path = doc_dir / "text.txt"
    if not text_path.exists():
        raise HTTPException(404, "Text not found")
    return FileResponse(text_path, media_type="text/plain")

@router.put("/doc/{doc_id}/edit")
def edit_data(
    doc_id: str,
    title: str = Form(...),                
    valid_from: str = Form(...),
    type : str = Form(...),
    valid_until: Optional[str] = Form(None),
    version: Optional[str] = Form(None),   
    file: UploadFile = File(...)             
):
    doc_dir = find_doc_dir_by_id(doc_id)
    if not doc_dir:
        raise HTTPException(404, "Document not found")

    if file.content_type != "text/plain":
        raise HTTPException(400, "Only .txt allowed")
    
    (doc_dir / "text.txt").write_text(
        file.file.read().decode("utf-8"),
        encoding="utf-8"
    )

    meta = load_meta(doc_dir / "meta.json")
    meta.title = title
    meta.valid_from = parse_date(valid_from)
    meta.valid_until = parse_date(valid_until) if valid_until else None
    meta.version = version
    meta.type = type
    
    (doc_dir / "meta.json").write_text(
        meta.model_dump_json(ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    return {"status": "updated", "doc_id": doc_id}



@router.get("/doc/{doc_id}/meta", response_model=DocumentMeta)
def get_metadata(doc_id: str):
    doc_dir = find_doc_dir_by_id(doc_id)
    if not doc_dir:
        raise HTTPException(404, "Document not found")
    return load_meta(doc_dir / "meta.json")

