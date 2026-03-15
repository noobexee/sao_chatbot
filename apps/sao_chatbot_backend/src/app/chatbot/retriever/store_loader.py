import json
import logging
import os
from typing import Any, Dict, List, Optional, Tuple

from pythainlp import word_tokenize
from rank_bm25 import BM25Okapi

from src.db.vector_store.vector_store import load_faiss_index

logger = logging.getLogger(__name__)


def load_master_map(path: str) -> Dict:
    """Loads a JSON mapping file, returning an empty dict if the file is missing."""
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def _build_bm25_corpus(metadata: List[Dict]) -> List[List[str]]:
    """Tokenises each document's text field to build a BM25 corpus."""
    corpus = []
    for i, doc in enumerate(metadata):
        try:
            text = str(doc.get("text", "")).lower()
            tokens = word_tokenize(text, engine="newmm") if text.strip() else ["empty"]
        except Exception as e:
            logger.error(f"Failed to tokenise document at index {i}: {e}")
            tokens = ["error"]
        corpus.append(tokens)
    return corpus


def load_store(path: str) -> Tuple[Optional[Any], List[Dict], Optional[BM25Okapi]]:
    """
    Loads a FAISS index and its metadata from disk, then builds a BM25 index.
    Returns (faiss_index, metadata, bm25) — any component may be None on failure.
    """
    try:
        index, metadata = load_faiss_index(path)

        if not metadata:
            logger.warning(f"No metadata found at '{path}'.")
            return index, [], None

        corpus = _build_bm25_corpus(metadata)
        bm25 = BM25Okapi(corpus) if corpus else None
        return index, metadata, bm25

    except Exception as e:
        logger.critical(f"Could not load search resources at '{path}': {e}")
        return None, [], None
