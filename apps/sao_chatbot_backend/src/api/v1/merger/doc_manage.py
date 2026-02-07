from fastapi import APIRouter, HTTPException, UploadFile, File, BackgroundTasks, Form
from fastapi.responses import Response, StreamingResponse
from typing import Optional, List
from datetime import datetime, date
from io import BytesIO
from urllib.parse import quote
from src.app.document.documentManage import manager

router = APIRouter()

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

@router.get("/doc")
def list_documents():
    return manager.list_documents()

@router.get("/doc/{doc_id}/original")
def get_original_pdf(doc_id: str):
    try:
        file_name, pdf_bytes = manager.get_original_pdf(doc_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    if isinstance(file_name, bytes):
        file_name = file_name.decode("utf-8", errors="ignore")

    if not file_name:
        file_name = "document.pdf"

    ascii_fallback = "document.pdf"
    utf8_filename = quote(file_name)

    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={
            "Content-Disposition": (
                f'inline; filename="{ascii_fallback}"; '
                f"filename*=UTF-8''{utf8_filename}"
            )
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

    main_pdf_bytes = main_file.file.read()

    result = manager.create_document(
        doc_type=doc_type,
        title=title,
        announce_date=announce_date,
        effective_date=effective_date,
        is_first_version=is_first_version,
        previous_doc_id=previous_doc_id,
        main_file_name=main_file.filename,
        main_file_bytes=main_pdf_bytes,
        related_files=[
            (rf.filename, rf.file.read()) for rf in related_files
        ] if related_files else None,
    )

    background_tasks.add_task(
        manager.handle_ocr,
        doc_id=result["id"],
        pdf_bytes=main_pdf_bytes,
    )

    return result




@router.get("/doc/{doc_id}/status")
def get_status(doc_id: str):
    try:
        return manager.get_status(doc_id)
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

    try:
        manager.edit_document(
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
    try:
        text = manager.get_text(doc_id)
    except ValueError as e:
        raise HTTPException(404, str(e))

    return Response(
        content=text,
        media_type="text/plain; charset=utf-8",
    )


@router.get("/doc/{doc_id}/meta")
def get_metadata(doc_id: str):
    try:
        return manager.get_metadata(doc_id)
    except ValueError as e:
        raise HTTPException(404, str(e))


@router.delete("/doc/{doc_id}")
def delete_document(doc_id: str):
    try:
        manager.delete_document(doc_id)
    except ValueError as e:
        raise HTTPException(404, str(e))

    return {
        "status": "deleted",
        "doc_id": doc_id,
    }
