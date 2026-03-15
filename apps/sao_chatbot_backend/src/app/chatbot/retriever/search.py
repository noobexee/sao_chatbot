import logging
from typing import Any, Dict, List, Optional

import numpy as np
from pythainlp import word_tokenize

from src.app.chatbot.constants import RRF_C

logger = logging.getLogger(__name__)

def run_rrf_fusion(
    vector_results: List[Dict],
    keyword_results: List[Dict],
    metadata_list: List[Dict],
    k: int,
    v_weight: float = 0.5,
) -> List[Dict]:
    """
    Combines vector and keyword result lists using Reciprocal Rank Fusion (RRF).
    Returns up to k merged, scored documents from metadata_list.
    """
    rrf_scores: Dict[int, float] = {}

    for item in vector_results:
        idx = item["idx"]
        rrf_scores[idx] = rrf_scores.get(idx, 0) + v_weight / (item["rank"] + RRF_C)

    for item in keyword_results:
        idx = item["idx"]
        rrf_scores[idx] = rrf_scores.get(idx, 0) + (1 - v_weight) / (item["rank"] + RRF_C)

    sorted_indices = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)

    matches = []
    for idx, score in sorted_indices:
        if idx < len(metadata_list):
            doc = metadata_list[idx].copy()
            doc["hybrid_score"] = score
            matches.append(doc)

    return matches

def _embed_and_search(embedder, index, query_text: str, k: int) -> List[Dict]:
    vec = embedder.embed_query(query_text)
    query_array = np.atleast_2d(vec).astype("float32")
    _, I = index.search(query_array, k * 5)
    return [{"idx": int(idx), "rank": i} for i, idx in enumerate(I[0]) if idx != -1]


def _tokenize_keywords(keyword_list: List[str]) -> List[str]:
    tokens = []
    for phrase in keyword_list:
        tokens.extend(word_tokenize(phrase.lower(), engine="newmm"))
    return tokens


def _bm25_search(bm25, keyword_list: List[str], k: int) -> List[Dict]:
    tokens = _tokenize_keywords(keyword_list)
    if not tokens:
        return []
    scores = bm25.get_scores(tokens)
    top_idx = np.argsort(scores)[::-1][: k * 5]
    return [{"idx": int(i), "rank": r} for r, i in enumerate(top_idx) if scores[i] > 0]

def vector_search_regulation(embedder, reg_index, query_text: str, k: int) -> List[Dict]:
    if not reg_index:
        logger.warning("Regulation FAISS index not loaded.")
        return []
    try:
        return _embed_and_search(embedder, reg_index, query_text, k)
    except Exception as e:
        logger.error(f"Vector search failed for regulations: {e}")
        return []


def keyword_search_regulation(reg_bm25, keyword_list: List[str], k: int) -> List[Dict]:
    if not reg_bm25 or not keyword_list:
        return []
    try:
        return _bm25_search(reg_bm25, keyword_list, k)
    except Exception as e:
        logger.error(f"BM25 search failed for regulations: {e}")
        return []


async def hybrid_search_regulation(
    embedder,
    reg_index,
    reg_bm25,
    reg_metadata: List[Dict],
    query: str,
    keywords: List[str],
    k: int = 5,
) -> List[Dict]:
    """Runs vector + keyword search on regulations and fuses results via RRF."""
    vec_res = vector_search_regulation(embedder, reg_index, query, k)
    key_res = keyword_search_regulation(reg_bm25, keywords, k)
    return run_rrf_fusion(vec_res, key_res, reg_metadata, k)

def vector_search_other(embedder, other_index, query_text: str, k: int) -> List[Dict]:
    if not other_index:
        logger.warning("Other-documents FAISS index not loaded.")
        return []
    try:
        return _embed_and_search(embedder, other_index, query_text, k)
    except Exception as e:
        logger.error(f"Vector search failed for other documents: {e}")
        return []


def keyword_search_other(other_bm25, keyword_list: List[str], k: int) -> List[Dict]:
    if not other_bm25 or not keyword_list:
        return []
    try:
        return _bm25_search(other_bm25, keyword_list, k)
    except Exception as e:
        logger.error(f"BM25 search failed for other documents: {e}")
        return []


async def hybrid_search_other(
    embedder,
    other_index,
    other_bm25,
    other_metadata: List[Dict],
    query: str,
    keywords: List[str],
    k: int = 5,
) -> List[Dict]:
    vec_res = vector_search_other(embedder, other_index, query, k)
    key_res = keyword_search_other(other_bm25, keywords, k)
    return run_rrf_fusion(vec_res, key_res, other_metadata, k)
