import asyncio
import logging
from threading import Lock
from typing import Dict, List, Optional

from src.app.llm.llm_manager import get_llm
from src.app.utils.embedding import global_embedder

from .filters import filter_by_date
from .query_rewriter import extract_keywords, rewrite_query_with_history
from .search import hybrid_search_other, hybrid_search_regulation
from .store_loader import load_master_map, load_store
from .document_mapper import fetch_exact_parent_regulations, fetch_related_other_documents
from src.app.chatbot.constants import (
    REGULATION_PATH,
    OTHERS_PATH,
    MASTER_MAP_PATH,
    SOURCE_MAP_PATH,
    DEFAULT_RETRIEVE_K,
    RELATED_DOCS_K,
    FETCH_MULTIPLIER,
)

_DOC_TYPE_BOOSTS = {
    "ระเบียบ": 1.30,
    "คำสั่ง": 1.10,
    "หลักเกณฑ์": 1.05,
}

logger = logging.getLogger(__name__)

class Retriever:
    def __init__(self):
        self.embedder = global_embedder
        self.llm = get_llm().get_model()
        self.search_lock = Lock()

        self.master_map: Dict = {}
        self.source_map: Dict = {}

        self.reg_index = None
        self.reg_metadata: List[Dict] = []
        self.reg_bm25 = None

        self.other_index = None
        self.other_metadata: List[Dict] = []
        self.other_bm25 = None

        self._reload_resources()

    def _reload_resources(self) -> None:
        logger.info("Reloading retriever resources...")
        self.master_map = load_master_map(MASTER_MAP_PATH)
        self.source_map = load_master_map(SOURCE_MAP_PATH)
        self.reg_index, self.reg_metadata, self.reg_bm25 = load_store(REGULATION_PATH)
        self.other_index, self.other_metadata, self.other_bm25 = load_store(OTHERS_PATH)

    async def _effective_query(self, query: str, history: list) -> str:
        return await rewrite_query_with_history(self.llm, query, history)

    async def _keywords(self, query: str) -> List[str]:
        return await extract_keywords(self.llm, query)

    async def _hybrid_regulation(self, query: str, keywords: List[str], k: int) -> List[Dict]:
        return await hybrid_search_regulation(
            self.embedder,
            self.reg_index,
            self.reg_bm25,
            self.reg_metadata,
            query,
            keywords,
            k,
        )

    async def _hybrid_other(self, query: str, keywords: List[str], k: int) -> List[Dict]:
        return await hybrid_search_other(
            self.embedder,
            self.other_index,
            self.other_bm25,
            self.other_metadata,
            query,
            keywords,
            k,
        )

    def _related_other(self, reg, query, keywords, seen, search_date, k=DEFAULT_RETRIEVE_K):
        return fetch_related_other_documents(
            self.master_map,
            self.embedder,
            self.other_index,
            self.other_bm25,
            self.other_metadata,
            reg,
            query,
            keywords,
            seen,
            search_date,
            k,
        )

    def _parent_regulations(self, cand: Dict, search_date: Optional[str], k=DEFAULT_RETRIEVE_K) -> List[Dict]:
        return fetch_exact_parent_regulations(
            self.source_map, self.reg_metadata, cand, search_date, k
        )

    async def retrieve_regulation(
        self,
        user_query: str,
        k: int = DEFAULT_RETRIEVE_K,
        history: list = [],
        search_date: Optional[str] = None,
    ) -> List[Dict]:
        try:
            effective_query = await self._effective_query(user_query, history)
            keywords = await self._keywords(effective_query)
            reg_results = await self._hybrid_regulation(effective_query, keywords, k)
            reg_results = filter_by_date(reg_results, k, search_date)

            seen_in_related: set = set()
            for reg in reg_results:
                try:
                    reg["related_documents"] = await self._related_other(
                        reg, effective_query, keywords, seen_in_related, search_date, k= RELATED_DOCS_K
                    )
                except Exception as e:
                    logger.error(f"Failed to fetch related documents for reg '{reg.get('id')}': {e}")
                    reg["related_documents"] = []

            return reg_results

        except Exception as e:
            logger.error(f"retrieve_regulation failed: {e}")
            return []

    async def retrieve_general(
        self,
        user_query: str,
        k: int = DEFAULT_RETRIEVE_K,
        history: list = [],
        search_date: Optional[str] = None,
    ) -> List[Dict]:
        try:
            effective_query = await self._effective_query(user_query, history)
            keywords = await self._keywords(effective_query)

            reg_candidates, other_candidates = await asyncio.gather(
                self._hybrid_regulation(effective_query, keywords, k * FETCH_MULTIPLIER),
                self._hybrid_other(effective_query, keywords, k * FETCH_MULTIPLIER),
            )

            reg_candidates = filter_by_date(reg_candidates or [], k * FETCH_MULTIPLIER, search_date)
            other_candidates = filter_by_date(other_candidates or [], k * FETCH_MULTIPLIER, search_date)

            seen_in_related: set = set()
            for reg in reg_candidates:
                reg["related_documents"] = await self._related_other(
                    reg, effective_query, keywords, seen_in_related, search_date, RELATED_DOCS_K
                )

            final_other_candidates = []
            for cand in other_candidates:
                unique_key = f"{cand.get('law_name')}|{cand.get('id')}"
                if unique_key not in seen_in_related:
                    cand["related_documents"] = self._parent_regulations(cand, search_date, RELATED_DOCS_K)
                    final_other_candidates.append(cand)

            all_candidates = reg_candidates + final_other_candidates
            self._apply_doc_type_boosts(all_candidates)
            all_candidates.sort(key=lambda x: x.get("hybrid_score", 0), reverse=True)
            return all_candidates[:k]

        except Exception as e:
            logger.error(f"retrieve_general failed: {e}")
            return []

    async def retrieve_order(
        self, user_query: str, k: int = DEFAULT_RETRIEVE_K, history: list = [], search_date: Optional[str] = None
    ) -> List[Dict]:
        return await self._retrieve_other_by_type(user_query, "คำสั่ง", k, search_date, history)

    async def retrieve_guideline(
        self, user_query: str, k: int = DEFAULT_RETRIEVE_K, history: list = [], search_date: Optional[str] = None
    ) -> List[Dict]:
        return await self._retrieve_other_by_type(user_query, "แนวทาง", k, search_date, history)

    async def retrieve_standard(
        self, user_query: str, k: int = DEFAULT_RETRIEVE_K, history: list = [], search_date: Optional[str] = None
    ) -> List[Dict]:
        return await self._retrieve_other_by_type(user_query, "หลักเกณฑ์", k, search_date, history)

    async def _retrieve_other_by_type(
        self,
        user_query: str,
        target_doc_type: str,
        k: int,
        search_date: Optional[str],
        history: list,
    ) -> List[Dict]:
        try:
            effective_query = await self._effective_query(user_query, history)
            keywords = await self._keywords(effective_query)

            candidates = await self._hybrid_other(effective_query, keywords, k * FETCH_MULTIPLIER)

            seen_chunks: set = set()
            filtered = []
            for cand in candidates:
                if target_doc_type not in cand.get("doc_type", ""):
                    continue
                unique_key = f"{cand.get('law_name')}|{cand.get('id')}"
                if unique_key not in seen_chunks:
                    filtered.append(cand)
                    seen_chunks.add(unique_key)

            return filter_by_date(filtered, k=k, search_date=search_date)

        except Exception as e:
            logger.error(f"_retrieve_other_by_type ('{target_doc_type}') failed: {e}")
            return []

    @staticmethod
    def _apply_doc_type_boosts(candidates: List[Dict]) -> None:
        """Mutates hybrid_score in-place based on document type."""
        for cand in candidates:
            law_name = cand.get("law_name") or ""
            doc_type = cand.get("doc_type") or ""
            combined = law_name + doc_type
            score = cand.get("hybrid_score", 0)

            for keyword, boost in _DOC_TYPE_BOOSTS.items():
                if keyword in combined:
                    cand["hybrid_score"] = score * boost
                    break
