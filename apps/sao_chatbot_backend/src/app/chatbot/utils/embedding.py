"""
BGE-M3 Embedding Model Wrapper

This module provides a wrapper for the BGE-M3 embedding model from HuggingFace.
Uses sentence-transformers library for efficient embedding generation.
"""

import numpy as np
from typing import List
import torch
from sentence_transformers import SentenceTransformer


class BGEEmbedder:
    """
    Wrapper for BGE-M3 embedding model.

    This class provides methods for embedding text chunks and queries
    using the BAAI/bge-m3 model from HuggingFace.

    Attributes:
        model_name: HuggingFace model identifier
        embedding_dimension: Output embedding dimension (1024 for BGE-M3)
        device: Device to run model on (cuda/cpu)
    """

    def __init__(self, model_name: str = "BAAI/bge-m3"):
        """
        Initialize BGE-M3 model from HuggingFace.

        Args:
            model_name: HuggingFace model identifier (default: BAAI/bge-m3)
        """
        self.model_name = model_name
        self._embedding_dimension = 1024

        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'

        print(f"Loading BGE-M3 model: {model_name}")
        print(f"Device: {self.device}")

        self.model = SentenceTransformer(model_name)
        self.model.to(self.device)

        print(f"Model loaded successfully")
        print(f"Embedding dimension: {self._embedding_dimension}")

    def embed_texts(self, texts: List[str], batch_size: int = 32, show_progress: bool = True) -> np.ndarray:
        """
        Embed list of text chunks using BGE-M3 model.

        Args:
            texts: List of text strings to embed
            batch_size: Batch size for encoding (default: 32)
            show_progress: Show progress bar during encoding (default: True)

        Returns:
            Numpy array of shape (n_texts, embedding_dim) as float32
        """
        n_texts = len(texts)
        print(f"Embedding {n_texts} texts with batch_size={batch_size}...")

        # Encode texts using BGE-M3
        embeddings = self.model.encode(
            texts,
            batch_size=batch_size,
            show_progress_bar=show_progress,
            convert_to_numpy=True,
            normalize_embeddings=True  
        )

        # Ensure float32 for FAISS
        embeddings = embeddings.astype(np.float32)

        print(f"✓ Generated embeddings: shape {embeddings.shape}")
        return embeddings

    def embed_query(self, query: str) -> np.ndarray:
        """
        Embed single query for retrieval.

        Args:
            query: Query string

        Returns:
            Numpy array of shape (1, embedding_dim) as float32
        """
        print(f"Embedding query: '{query[:50]}...'")

        # Encode query using BGE-M3
        embedding = self.model.encode(
            [query],
            batch_size=1,
            show_progress_bar=False,
            convert_to_numpy=True,
            normalize_embeddings=True  # BGE models benefit from normalization
        )

        # Ensure float32 and correct shape for FAISS
        embedding = embedding.astype(np.float32)

        print(f"✓ Generated query embedding: shape {embedding.shape}")
        return embedding

    @property
    def embedding_dimension(self) -> int:
        """
        Return embedding dimension.

        Returns:
            Embedding dimension (1024 for BGE-M3)
        """
        return self._embedding_dimension