import json
import os
import threading
import faiss
import numpy as np
from typing import List, Dict, Any, Optional

_path_locks: Dict[str, threading.Lock] = {}
_lock_registry_access = threading.Lock()

def get_lock_for_path(path: str) -> threading.Lock:
    """Gets or creates a lock specific to a directory path."""
    with _lock_registry_access:
        if path not in _path_locks:
            _path_locks[path] = threading.Lock()
        return _path_locks[path]

class VectorStoreTransaction:
    """
    A transactional wrapper for a SINGLE FAISS index at a specific path.
    """
    def __init__(self, path: str):
        self.path = path
        self.index = None
        self.metadata = []
        self.lock = get_lock_for_path(path)

    def __enter__(self):
        # Acquire the lock for THIS specific folder
        acquired = self.lock.acquire(timeout=20.0)
        if not acquired:
            raise TimeoutError(f"Could not acquire lock for {self.path}. It is busy.")
        
        try:
            os.makedirs(self.path, exist_ok=True)
            index_path = os.path.join(self.path, "index.faiss")
            metadata_path = os.path.join(self.path, "metadata.json")
            
            if os.path.exists(index_path) and os.path.exists(metadata_path):
                self.index = faiss.read_index(index_path)
                with open(metadata_path, 'r', encoding='utf-8') as f:
                    self.metadata = json.load(f)
            return self
        except Exception as e:
            self.lock.release()
            raise e

    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            if exc_type is None and self.index is not None:
                faiss.write_index(self.index, os.path.join(self.path, "index.faiss"))
                
                meta_path = os.path.join(self.path, "metadata.json")
                tmp_path = meta_path + ".tmp"
                with open(tmp_path, 'w', encoding='utf-8') as f:
                    json.dump(self.metadata, f, ensure_ascii=False, indent=2)
                
                os.replace(tmp_path, meta_path)
                print(f"[{self.path}] Transaction committed: {self.index.ntotal} vectors.")
            elif exc_type is not None:
                print(f"[{self.path}] Transaction rolled back: {exc_val}")
        finally:
            self.lock.release()

    def add(self, embeddings: np.ndarray, chunks: List[dict]):
        if self.index is None:
            dim = embeddings.shape[1]
            self.index = faiss.IndexFlatL2(dim)
        
        if embeddings.dtype != np.float32:
            embeddings = embeddings.astype(np.float32)
            
        self.index.add(embeddings)
        self.metadata.extend(chunks)

    def delete_by_filter(self, key: str, value: Any):
        if not self.index: return
        
        ids_to_remove = [i for i, m in enumerate(self.metadata) if m.get(key) == value]
        if ids_to_remove:
            self.index.remove_ids(np.array(ids_to_remove).astype('int64'))
            for i in sorted(ids_to_remove, reverse=True):
                del self.metadata[i]
            print(f"[{self.path}] Deleted {len(ids_to_remove)} vectors where {key}={value}")

    def update_metadata_field(self, filter_key: str, filter_value: Any, update_key: str, new_value: Any):
        updated_count = 0
        for entry in self.metadata:
            if entry.get(filter_key) == filter_value:
                entry[update_key] = new_value
                updated_count += 1
        if updated_count > 0:
            print(f"[{self.path}] Updated metadata for {updated_count} chunks.")

class LegalVectorSystem:
    """
    Manages the split between Regulations and Others.
    """
    def __init__(self, base_storage_path: str):
        self.reg_path = os.path.join(base_storage_path, "regulations")
        self.other_path = os.path.join(base_storage_path, "others")

    def get_store(self, doc_type: str) -> str:
        """Returns the correct path based on document type."""
        if doc_type == "ระเบียบ":
            return self.reg_path
        return self.other_path

    def add_document(self, embeddings: np.ndarray, chunks: List[dict], doc_type: str):
        """Helper to add to the correct store automatically."""
        target_path = self.get_store(doc_type)

        with VectorStoreTransaction(target_path) as vs:
            vs.add(embeddings, chunks)

def load_faiss_index(load_path: str):
    """
    Safely reads an index, respecting its specific lock.
    """
    lock = get_lock_for_path(load_path)
    with lock:
        if not os.path.exists(os.path.join(load_path, "index.faiss")):
            return None, []
            
        index = faiss.read_index(os.path.join(load_path, "index.faiss"))
        with open(os.path.join(load_path, "metadata.json"), 'r', encoding='utf-8') as f:
            metadata = json.load(f)
        return index, metadata