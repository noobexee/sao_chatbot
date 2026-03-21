from datetime import date
from typing import Dict, List
from src.app.utils.chunking import chunk_by_clause, chunk_by_size
from src.app.utils.embedding import global_embedder
from src.app.utils.preprocess_dataset import (
    delete_document_pipeline,
    index_single_json_file,
    update_document_expiry_pipeline,
    update_document_pipeline,
)
from src.app.document.documentSchemas import DocumentMeta


class DocumentUpdater:
    def __init__(self):
        self.embedder = global_embedder
        
    def build_version_to_source_map(self, sources: list) -> Dict[int, str]:
        return {s["order"]: s["source_id"] for s in sources}

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
        
        
        if doc_data.type == "ระเบียบ" :
            chunks = chunk_by_clause(
            text=text,
            law_name=doc_data.title,
            announce_date=announce_date,
            effective_date=effective_date,
            version=doc_data.version,
            document_id=doc_id,
            doc_type=doc_data.type,
        )
            index_single_json_file(chunks, embedder=self.embedder, is_regulation=True)
        else :

            chunks = chunk_by_size(
            text=text,
            law_name=doc_data.title,
            announce_date=announce_date,
            effective_date=effective_date,
            version=doc_data.version,
            document_id=doc_id,
            doc_type=doc_data.type,
        )
            index_single_json_file(chunks, embedder=self.embedder, is_regulation=False)
        return len(chunks)

    # ---------- Edit ----------
    def edit_document(
        self,
        *,
        doc_data: DocumentMeta,
        doc_id: str,
        text: str,
        snapshot_sources: list,
        
    ) -> int:
        
        announce_date = str(doc_data.announce_date)
        effective_date = str(doc_data.effective_date)
        version_to_source = self.build_version_to_source_map(snapshot_sources)

        if doc_data.type == "ระเบียบ" :

            chunks = chunk_by_clause(
                text=text,
                law_name=doc_data.title,
                announce_date=announce_date,
                effective_date=effective_date,
                version=doc_data.version,
                document_id=doc_id,
                doc_type=doc_data.type,
                version_to_source=version_to_source
            )
        else :
            chunks = chunk_by_size(
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
        amend_doc_id: str,
        text: str,
        expire_date: date,
        snapshot_sources: list,
        
    ) -> int:
        print(snapshot_sources)
        announce_date = str(doc_data.announce_date)
        effective_date = str(doc_data.effective_date)
        expire_date = str(expire_date)
        version_to_source = self.build_version_to_source_map(snapshot_sources)
        delete_document_pipeline(amend_doc_id)
        update_document_expiry_pipeline(old_doc_id, expire_date)

        if doc_data.type == "ระเบียบ" :
            chunks = chunk_by_clause(
            text=text,
            law_name=doc_data.title,
            announce_date=announce_date,
            effective_date=effective_date,
            version=doc_data.version,
            document_id=new_doc_id,
            doc_type=doc_data.type,
            version_to_source=version_to_source
            )
            index_single_json_file(chunks, embedder=self.embedder, is_regulation=True)
        else :
            chunks = chunk_by_size(
            text=text,
            law_name=doc_data.title,
            announce_date=announce_date,
            effective_date=effective_date,
            version=doc_data.version,
            document_id=new_doc_id,
            doc_type=doc_data.type,
            )
            index_single_json_file(chunks, embedder=self.embedder, is_regulation=False)
        return len(chunks)

    # ---------- Delete ----------
    def delete_document(self, document_id: str):
        delete_document_pipeline(document_id)
        return "done"
