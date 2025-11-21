import faiss
import numpy as np
import json
import os

from src.config import settings


class VectorService:
    def __init__(self):
        self.index_path = settings.VECTOR_STORE_PATH

        if os.path.exists(self.index_path):
            self.index = faiss.read_index(self.index_path)
            with open(self.index_path + ".meta.json") as f:
                self.metadata = json.load(f)
        else:
            # Empty store
            self.index = faiss.IndexFlatL2(1536)  # depends on embedding size
            self.metadata = []

    def search(self, embedding, k=3):
        embedding = np.array([embedding]).astype("float32")
        D, I = self.index.search(embedding, k)
        return [self.metadata[i] for i in I[0] if i != -1]
