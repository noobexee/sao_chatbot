import json
import os
import threading
import faiss
import numpy as np
from typing import List, Tuple, Any

# Global lock to prevent simultaneous writes from different threads
_global_lock = threading.Lock()
LOCK_TIMEOUT = 20.0  # Seconds to wait before timing out

class VectorStoreTransaction:
    """
    A transactional wrapper for FAISS. 
    Usage:
        with VectorStoreTransaction("storage/path") as vs:
            vs.delete_by_filter("source", "old_file.json")
            vs.add(new_embeddings, new_metadata)
    """
    def __init__(self, path: str):
        self.path = path
        self.index = None
        self.metadata = []

    def __enter__(self):
        #  Block other threads
        acquired = _global_lock.acquire(timeout=LOCK_TIMEOUT)
        if not acquired:
            raise TimeoutError("Could not acquire lock. The index might be in use.")
        
        try:
            #  Load the current state from disk
            index_path = os.path.join(self.path, "index.faiss")
            metadata_path = os.path.join(self.path, "metadata.json")
            
            if os.path.exists(index_path) and os.path.exists(metadata_path):
                self.index = faiss.read_index(index_path)
                with open(metadata_path, 'r', encoding='utf-8') as f:
                    self.metadata = json.load(f)
            return self
        except Exception as e:
            _global_lock.release()
            raise e

    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            # If NO ERROR occurred inside the 'with' block, save changes
            if exc_type is None and self.index is not None:
                os.makedirs(self.path, exist_ok=True)
                
                # Save FAISS binary
                faiss.write_index(self.index, os.path.join(self.path, "index.faiss"))
                
                # Atomic Save Metadata
                meta_path = os.path.join(self.path, "metadata.json")
                tmp_path = meta_path + ".tmp"
                with open(tmp_path, 'w', encoding='utf-8') as f:
                    json.dump(self.metadata, f, ensure_ascii=False, indent=2)
                os.replace(tmp_path, meta_path)
                print(f"Transaction committed: {self.index.ntotal} total vectors.")
            elif exc_type is not None:
                print(f"Transaction rolled back due to error: {exc_val}")
        finally:
            # ALWAYS release the lock so other threads can work
            _global_lock.release()

    def add(self, embeddings: np.ndarray, chunks: List[dict]):
        """Internal helper to add data during the transaction."""
        if self.index is None:
            # Default to 1024 if index doesn't exist yet
            dim = embeddings.shape[1]
            self.index = faiss.IndexFlatL2(dim)
        
        if embeddings.dtype != np.float32:
            embeddings = embeddings.astype(np.float32)
            
        self.index.add(embeddings)
        self.metadata.extend(chunks)

    def delete_by_filter(self, key: str, value: Any):
        """Internal helper to remove data during the transaction."""
        if not self.index:
            return
        
        # Find indices while locked (guarantees they won't shift)
        ids_to_remove = [i for i, m in enumerate(self.metadata) if m.get(key) == value]
        
        if ids_to_remove:
            self.index.remove_ids(np.array(ids_to_remove).astype('int64'))
            # Delete metadata from back to front
            for i in sorted(ids_to_remove, reverse=True):
                del self.metadata[i]
            print(f"Deleted {len(ids_to_remove)} vectors matching {key}={value}")

# Keep this for your Retriever which only reads
def load_faiss_index(load_path: str):
    with _global_lock:
        index = faiss.read_index(os.path.join(load_path, "index.faiss"))
        with open(os.path.join(load_path, "metadata.json"), 'r', encoding='utf-8') as f:
            metadata = json.load(f)
        return index, metadata