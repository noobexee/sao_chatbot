import os
import json
from pathlib import Path
from typing import Optional, List
import numpy as np
from src.app.utils.embedding import BGEEmbedder
from src.db.vector_store.vector_store import VectorStoreTransaction 

BASE_STORAGE = "storage"
REGULATION_DIR = os.path.join(BASE_STORAGE, "regulations")  # For 'ระเบียบ'
OTHERS_DIR = os.path.join(BASE_STORAGE, "others")          # For 'แนวทาง', 'คำสั่ง'

def index_single_json_file(chunks: list, embedder: BGEEmbedder, is_regulation: bool = False):
    """
    Now determines the destination purely based on the 'is_regulation' flag.
    """ 
    if not chunks:
        return
    if is_regulation:
        target_path = REGULATION_DIR
    else:
        target_path = OTHERS_DIR

    _embed_and_save(chunks, embedder, target_path)

def _embed_and_save(chunk_batch: List[dict], embedder: BGEEmbedder, target_path: str):
    """
    Internal Helper: Embeds a batch and saves it to the specific target path.
    """
    try:
        texts = [c.get('text', '') for c in chunk_batch]
        
        new_embeddings = embedder.embed_texts(texts, batch_size=16)
        
        with VectorStoreTransaction(target_path) as vs:              
            vs.add(new_embeddings, chunk_batch)
            print(f"Indexed {len(chunk_batch)} chunks to {target_path}")
            
    except Exception as e:
        print(f"Failed to index batch to {target_path}")
        print(f"{str(e)}")

def run_indexing_pipeline(metadata_folder: str, is_regulation_folder: bool = False):
    """
    Bulk function: Accepts the flag to pass down to the indexer.
    """
    print(f"\nStarting Bulk Indexing for Folder: {metadata_folder} (Regulation={is_regulation_folder})")
    embedder = BGEEmbedder()
    
    json_files = list(Path(metadata_folder).glob("**/*.json"))
    
    if not json_files:
        print("No files found to index.")
        return

    for file_path in json_files:
        filename = file_path.name
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                chunks = json.load(f)
            
            # Pass the flag here
            index_single_json_file(chunks, embedder, is_regulation=is_regulation_folder)
            
        except Exception as e:
            print(f"Error reading {filename}: {e}")
    
    print(f"Bulk indexing of {len(json_files)} files complete.")

def delete_document_pipeline(document_id: str):
    """
    Robust Deletion: Iterates through BOTH vector stores and removes the document 
    if it exists. This ensures we don't leave 'ghost' versions if a document 
    changed type (e.g. from 'Others' to 'Regulation').
    """
    print(f"Starting deletion for Document ID: {document_id}")
    
    # List of all stores to check
    target_stores = [REGULATION_DIR, OTHERS_DIR]
    
    for store_path in target_stores:
        try:
            with VectorStoreTransaction(store_path) as vs:
                vs.delete_by_filter("document_id", document_id)
                
        except Exception as e:
            print(f"Warning: Could not access {store_path} during deletion: {e}")

    print(f"Deletion process finished for {document_id}")

def update_document_pipeline(document_id: str, new_chunks: List[dict], embedder: BGEEmbedder, is_regulation: Optional[bool] = None):
    """
    Updates a document by:
    1. Using the provided is_regulation flag OR auto-detecting it from the first chunk.
    2. Deleting the old version from ALL stores (Regulation & Others).
    3. Re-indexing the new version into the correct store.
    """
    print(f"Starting update for Document ID: {document_id}")
    
    if not new_chunks:
        print("Warning: new_chunks is empty. Aborting update.")
        return

    if is_regulation is not None:
        target_is_regulation = is_regulation
        print(f"Using provided flag: is_regulation={target_is_regulation}")
        
    else:
        first_doc_type = new_chunks[0].get("doc_type", "")
        if first_doc_type == "ระเบียบ":
            target_is_regulation = True
            print(f"Auto-detected type: Regulation ('{first_doc_type}')")
        else:
            target_is_regulation = False
            print(f"Auto-detected type: Others ('{first_doc_type}')")

    delete_document_pipeline(document_id)
    
    try:
        index_single_json_file(new_chunks, embedder, is_regulation=target_is_regulation)
        print(f"Successfully updated Document ID: {document_id}")
    except Exception as e:
        print(f"Error during re-indexing of {document_id}: {e}")

def update_document_expiry_pipeline(document_id: str, new_expiry: str = "2999-01-01"):
    """
    Updates metadata in BOTH stores.
    """
    print(f"Updating expiry date for Document ID: {document_id} to {new_expiry}")
    
    target_stores = [REGULATION_DIR, OTHERS_DIR]
    
    for store_path in target_stores:
        try:
            with VectorStoreTransaction(store_path) as vs:
                vs.update_metadata_field(
                    filter_key="document_id", 
                    filter_value=document_id, 
                    update_key="expire_date", 
                    new_value=new_expiry
                )
        except Exception as e:
            print(f"Error updating expiry in {store_path}: {e}")
            
    print(f"Expiry update complete for {document_id}")
    """
    Updates metadata in BOTH stores to ensure consistency.
    """
    print(f"Updating expiry date for Document ID: {document_id} to {new_expiry}")
    
    stores = [REGULATION_DIR, OTHERS_DIR]
    
    for store_path in stores:
        try:
            with VectorStoreTransaction(store_path) as vs:
                vs.update_metadata_field(
                    filter_key="document_id", 
                    filter_value=document_id, 
                    update_key="expire_date", 
                    new_value=new_expiry
                )
        except Exception as e:
            print(f"Error updating expiry in {store_path}: {e}")
            
    print(f"Expiry update complete for {document_id}")