from fastapi import APIRouter, HTTPException
from src.app.document.documentSchemas import MergeRequest
from src.app.document.documentManage import manager

router = APIRouter()


@router.put("/merge")
def merge_documents(payload: MergeRequest):
    try:
        result = manager.merge_documents(
            base_doc_id=payload.base_doc_id,
            amend_doc_id=payload.amend_doc_id,
            merge_mode=payload.merge_mode,
        )
    except ValueError as e:
        raise HTTPException(404, str(e))

    return {
        "status": "success",
        **result,
        "text_endpoint": f"/doc/{result['id']}/text",
        "meta_endpoint": f"/doc/{result['id']}/meta",
    }
