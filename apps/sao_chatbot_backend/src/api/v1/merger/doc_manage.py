from fastapi.responses import FileResponse
from fastapi import APIRouter, HTTPException, UploadFile, File, BackgroundTasks, Form
from pathlib import Path
import uuid
import shutil
from typing import Optional, List
from datetime import datetime, date
import json
from src.app.service.ocr_service import run_ocr_job
from src.app.manager.document import DocumentMeta

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
    docs = []

    if not MOCK_DIR.exists():
        return docs

    for type_dir in MOCK_DIR.iterdir():
        if not type_dir.is_dir():
            continue

        for doc_dir in type_dir.iterdir():
            meta_path = doc_dir / "meta.json"
            status_path = doc_dir / "status.txt"

            if not meta_path.exists() or not status_path.exists():
                continue

            meta = load_meta(meta_path)
            docs.append({
                "id": doc_dir.name,
                **meta.dict(),
                "status": status_path.read_text().strip()
            })

    return docs

@router.get("/doc/{doc_id}/original")
def get_original_pdf(doc_id: str):
    doc_dir = find_doc_dir_by_id(doc_id)
    if not doc_dir:
        raise HTTPException(404, "Document not found")

    pdfs = list(doc_dir.glob("*.pdf"))
    if not pdfs:
        raise HTTPException(404, "PDF not found")

    pdf = pdfs[0]
    return FileResponse(
        pdf,
        media_type="application/pdf",
        filename=pdf.name
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

    base_meta: Optional[DocumentMeta] = None

    if previous_doc_id:
        base_dir = find_doc_dir_by_id(previous_doc_id)
        if not base_dir:
            raise HTTPException(400, "previous document not found")

        base_meta = DocumentMeta.model_validate_json(
            (base_dir / "meta.json").read_text(encoding="utf-8")
        )
    if base_meta:
        safe_type = base_meta.type
        derived_title = base_meta.title
        version = base_meta.version + 1
        mark_previous_not_latest(safe_type, derived_title)
    else:
        safe_type = doc_type.strip().lower().replace(" ", "_")
        derived_title = derive_title(main_file, title)
        version = 1 if is_first_version else get_next_version(safe_type, derived_title)
        if not is_first_version:
            mark_previous_not_latest(safe_type, derived_title)
    pdf_filename = f"{derived_title}.pdf"
    doc_id = str(uuid.uuid4())
    doc_dir = MOCK_DIR / safe_type / doc_id
    doc_dir.mkdir(parents=True, exist_ok=True)

    main_pdf_path = doc_dir / pdf_filename
    with main_pdf_path.open("wb") as f:
        shutil.copyfileobj(main_file.file, f)
    related_form_id: Optional[List[str]] = None
    if related_files:
        related_form_id = []

        for rf in related_files:
            rel_id = str(uuid.uuid4())
            related_form_id.append(rel_id)

            rel_dir = doc_dir / rel_id
            rel_dir.mkdir(parents=True, exist_ok=True)

            with (rel_dir / rf.filename).open("wb") as out:
                shutil.copyfileobj(rf.file, out)
    meta = DocumentMeta(
        title=derived_title,
        type=safe_type,
        announce_date=announce_date,
        effective_date=effective_date,
        version=version,
        is_snapshot=False,
        is_latest=True,
        related_form_id=related_form_id,
    )
    (doc_dir / "meta.json").write_text(
        meta.model_dump_json(ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    (doc_dir / "text.txt").write_text("", encoding="utf-8")
    (doc_dir / "status.txt").write_text("queued", encoding="utf-8")
    background_tasks.add_task(run_ocr_job, main_pdf_path)

    return {
        "id": doc_id,
        "title": meta.title,
        "version": meta.version,
        "related_form_id": meta.related_form_id,
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

@router.put("/doc/{doc_id}/edit")
def edit_doc(
    doc_id: str,
    title: str = Form(...),
    type: str = Form(...),
    announce_date: str = Form(...),
    effective_date: Optional[str] = Form(None),
    file: UploadFile = File(...),
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
    meta_path = doc_dir / "meta.json"
    meta = load_meta(meta_path)
    meta.title = title.strip()
    meta.type = type.strip().lower().replace(" ", "_")
    meta.announce_date = parse_date(announce_date)
    meta.effective_date = (
        parse_date(effective_date) if effective_date else None
    )
    meta_path.write_text(
        meta.model_dump_json(ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    return {
        "status": "updated",
        "doc_id": doc_id,
    }



@router.get("/doc/{doc_id}/text")
def get_text(doc_id: str):
    doc_dir = find_doc_dir_by_id(doc_id)
    if not doc_dir:
        raise HTTPException(404, "Document not found")

    return FileResponse(doc_dir / "text.txt", media_type="text/plain")

@router.get("/doc/{doc_id}/meta", response_model=DocumentMeta)
def get_metadata(doc_id: str):
    doc_dir = find_doc_dir_by_id(doc_id)
    if not doc_dir:
        raise HTTPException(404, "Document not found")

    return load_meta(doc_dir / "meta.json")

@router.delete("/doc/{doc_id}")
def delete_document(doc_id: str):
    doc_dir = find_doc_dir_by_id(doc_id)
    if not doc_dir:
        raise HTTPException(404, "Document not found")

    shutil.rmtree(doc_dir)
    return {"status": "deleted", "doc_id": doc_id}
