import os
import json
from pathlib import Path
import numpy as np
from src.app.chatbot.utils.embedding import BGEEmbedder
from src.db.vector_store import VectorStoreTransaction

VECTOR_STORE_DIR = "storage/faiss_index"

def index_single_json_file(chunks: list, embedder: BGEEmbedder,):
    """
    Atomic update: Embeds chunks and updates the vector store in a single transaction.
    """ 
    if not chunks:
        return
    texts = [c.get('text', '') for c in chunks]
    new_embeddings = embedder.embed_texts(texts, batch_size=16)
    
    try:
        with VectorStoreTransaction(VECTOR_STORE_DIR) as vs:              
            vs.add(new_embeddings, chunks)
        
    except Exception as e:
        print(f"Failed to index {chunks[0].law_name}: {str(e)}")

def run_indexing_pipeline(metadata_folder: str):
    """
    Bulk function: Processes every file in the folder using atomic transactions.
    """
    print(f"\nStarting Bulk Indexing for Folder: {metadata_folder}")
    embedder = BGEEmbedder()
    
    json_files = list(Path(metadata_folder).glob("**/*.json"))
    
    if not json_files:
        print("No files found to index.")
        return

    for file_path in json_files:
        filename = file_path.name
        print(f"Processing {filename}...")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            chunks = json.load(f)
            
        index_single_json_file(chunks, embedder, filename)
    
    print(f"Bulk indexing of {len(json_files)} files complete.")

def delete_document_pipeline(document_id: str):
    """
    Completely removes all chunks associated with a document_id.
    """
    print(f"Starting deletion for Document ID: {document_id}")
    try:
        with VectorStoreTransaction(VECTOR_STORE_DIR) as vs:
            # Atomic delete using the filter we built
            vs.delete_by_filter("document_id", document_id)
        print(f"Successfully deleted Document ID: {document_id}")
    except Exception as e:
        print(f"Error during deletion of {document_id}: {e}")

def update_document_pipeline(document_id: str, new_chunks: list, embedder: BGEEmbedder):
    """
    Updates a document by removing the old version and adding the new version.
    This is handled as a single atomic transaction.
    """
    print(f"Starting update for Document ID: {document_id}")
    
    texts = [c.get('text', '') for c in new_chunks]
    new_embeddings = embedder.embed_texts(texts, batch_size=16)
    try:
        with VectorStoreTransaction(VECTOR_STORE_DIR) as vs:
            # Remove old version
            vs.delete_by_filter("document_id", document_id)
            # Add new version
            vs.add(new_embeddings, new_chunks)
            
        print(f"Successfully updated Document ID: {document_id}")
    except Exception as e:
        print(f"Error during update of {document_id}: {e}")