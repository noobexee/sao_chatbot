from datetime import date
from src.app.utils.chunking import chunk_by_clause
from src.app.utils.embedding import BGEEmbedder
from src.app.utils.preprocess_dataset import (
    delete_document_pipeline,
    index_single_json_file,
    update_document_expiry_pipeline,
    update_document_pipeline,
)
from src.app.document.documentSchemas import DocumentMeta


class DocumentUpdater:
    def __init__(self):
        self.embedder = BGEEmbedder()

    # ---------- Create ----------

    def new_document(
        self,
        *,
        doc_data: DocumentMeta,
        doc_id: str,
        text: str,
    ) -> int:
        
        announce_date = str(doc_data.announce_date)
        effective_date = str(doc_data.effective_date)

        chunks = chunk_by_clause(
            text=text,
            law_name=doc_data.title,
            announce_date=announce_date,
            effective_date=effective_date,
            version=doc_data.version,
            document_id=doc_id,
            doc_type=doc_data.type,
        )

        index_single_json_file(chunks, embedder=self.embedder)
        return len(chunks)

    # ---------- Edit ----------

    def edit_document(
        self,
        *,
        doc_data: DocumentMeta,
        doc_id: str,
        text: str,
    ) -> int:
        
        announce_date = str(doc_data.announce_date)
        effective_date = str(doc_data.effective_date)

        chunks = chunk_by_clause(
            text=text,
            law_name=doc_data.title,
            announce_date=announce_date,
            effective_date=effective_date,
            version=doc_data.version,
            document_id=doc_id,
            doc_type=doc_data.type,
        )

        update_document_pipeline(doc_id, chunks, embedder=self.embedder)
        return len(chunks)

    # ---------- Merge / Snapshot ----------

    def merge_documents(
        self,
        *,
        doc_data: DocumentMeta,
        old_doc_id: str,
        new_doc_id: str,
        text: str,
        expire_date: date,
    ) -> int:
        
        announce_date = str(doc_data.announce_date)
        effective_date = str(doc_data.effective_date)
        expire_date = str(expire_date)

        update_document_expiry_pipeline(old_doc_id, expire_date)

        chunks = chunk_by_clause(
            text=text,
            law_name=doc_data.title,
            announce_date=announce_date,
            effective_date=effective_date,
            version=doc_data.version,
            document_id=new_doc_id,
            doc_type=doc_data.type,
        )

        index_single_json_file(chunks, embedder=self.embedder)
        return len(chunks)

    # ---------- Delete ----------

    def delete_document(self, document_id: str):
        delete_document_pipeline(document_id)
        return "done"
