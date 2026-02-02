"""
FAISS vector store utilities.

This module provides functions for creating, saving, and loading
FAISS indices with associated metadata.
"""

import json
import os
from typing import List, Tuple

import faiss
import numpy as np


def create_faiss_index(dimension: int) -> faiss.IndexFlatL2:
    """
    Initialize FAISS index with specified dimension.

    Args:
        dimension: Embedding dimension (1024 for BGE-M3)

    Returns:
        FAISS IndexFlatL2 for exact L2 distance search

    Note:
        IndexFlatL2 performs exact search using L2 (Euclidean) distance.
        For larger datasets, consider using IndexIVFFlat for faster approximate search.
    """
    index = faiss.IndexFlatL2(dimension)
    return index


def save_faiss_index(
    index: faiss.Index,
    metadata: List[dict],
    save_path: str
):
    """
    Persist FAISS index and metadata to disk.

    Args:
        index: FAISS index to save
        metadata: List of chunk metadata dictionaries
        save_path: Directory path to save index and metadata

    Creates:
        - {save_path}/index.faiss: Binary FAISS index
        - {save_path}/metadata.json: Chunk metadata array

    Note:
        Document mapping is already in storage/doc_mapping.json
        This metadata only contains chunk-level information
    """
    # Ensure save directory exists
    os.makedirs(save_path, exist_ok=True)

    # Save FAISS index
    index_path = os.path.join(save_path, "index.faiss")
    faiss.write_index(index, index_path)

    # Save metadata
    metadata_path = os.path.join(save_path, "metadata.json")
    with open(metadata_path, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)

    print(f"Saved FAISS index to: {index_path}")
    print(f"Saved metadata to: {metadata_path}")
    print(f"Total vectors: {index.ntotal}")


def load_faiss_index(load_path: str) -> Tuple[faiss.Index, List[dict]]:
    """
    Load persisted FAISS index and metadata.

    Args:
        load_path: Directory containing index and metadata files

    Returns:
        Tuple of (index, metadata_list)

    Raises:
        FileNotFoundError: If index or metadata files don't exist
    """
    index_path = os.path.join(load_path, "index.faiss")
    metadata_path = os.path.join(load_path, "metadata.json")

    if not os.path.exists(index_path):
        raise FileNotFoundError(f"FAISS index not found at: {index_path}")

    if not os.path.exists(metadata_path):
        raise FileNotFoundError(f"Metadata not found at: {metadata_path}")

    # Load FAISS index
    index = faiss.read_index(index_path)

    # Load metadata
    with open(metadata_path, 'r', encoding='utf-8') as f:
        metadata = json.load(f)

    print(f"Loaded FAISS index from: {index_path}")
    print(f"Total vectors: {index.ntotal}")
    print(f"Total metadata entries: {len(metadata)}")

    return index, metadata


def add_embeddings_to_index(
    index: faiss.Index,
    embeddings: np.ndarray,
    metadata: List[dict]
) -> List[dict]:
    """
    Add new embeddings to FAISS index.

    Args:
        index: FAISS index to update
        embeddings: Numpy array of embeddings (shape: n_vectors x dimension)
        metadata: List of metadata dictionaries to append

    Returns:
        Updated metadata list

    Note:
        Embeddings must be float32 for FAISS
        Metadata list is returned (caller should save separately)
    """
    # Ensure embeddings are float32
    if embeddings.dtype != np.float32:
        embeddings = embeddings.astype(np.float32)

    # Add to index
    index.add(embeddings)

    print(f"Added {len(embeddings)} vectors to index")
    print(f"Total vectors in index: {index.ntotal}")

    return metadata
