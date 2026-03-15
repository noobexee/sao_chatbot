import asyncio
import logging
from typing import Any

from langchain_core.output_parsers import JsonOutputParser

from src.app.chatbot.router import get_legal_sub_route
from src.app.chatbot.utils.references import map_references_to_document_ids
from src.app.chatbot.utils.formatters import format_regulation_context
from src.app.chatbot.handlers.base import BaseHandler
from src.app.chatbot.prompts.legal_query import build_prompt
from src.app.chatbot.schemas import RAGResponse, LegalResponseSchema
from src.app.chatbot.constants import (
    DEFAULT_RETRIEVAL_K,
    HISTORY_WINDOW,
    LEGAL_ROUTE_ORDER,
    LEGAL_ROUTE_GUIDELINE,
    LEGAL_ROUTE_STANDARD,
    LEGAL_ROUTE_REGULATION,
)
from src.app.chatbot.retriever import Retriever

logger = logging.getLogger(__name__)

class LegalRagHandler(BaseHandler):

    _error_message = "ขออภัย ระบบขัดข้องในการประมวลผลข้อมูลทางกฎหมาย"

    def __init__(self, retriever: Retriever):
        self._retriever = retriever
        self._prompt = build_prompt()
        self._parser = JsonOutputParser(pydantic_object=LegalResponseSchema)

    async def handle(self, query: str, history: list, llm: Any) -> RAGResponse:
        route = await get_legal_sub_route(query, history, llm)
        retrieved_docs = await self._retrieve(query, history, route)
        history_str = self._format_history(history, window=HISTORY_WINDOW)
        context_str = format_regulation_context(retrieved_docs)

        chain = (
            {
                "context":             lambda x: context_str,
                "history":             lambda x: history_str,
                "query":               lambda x: query,
                "format_instructions": lambda x: self._parser.get_format_instructions(),
            }
            | self._prompt
            | llm
            | self._parser
        )

        try:
            result = await self._invoke(chain, {})
            return self._build_response(result, retrieved_docs)
        except asyncio.TimeoutError:
            logger.error("LegalRagHandler timed out")
            return self._error_response()
        except Exception as e:
            logger.error(f"LegalRagHandler failed: {e}", exc_info=True)
            return self._error_response()

    async def _retrieve(
        self, query: str, history: list, route: str
    ) -> list:
        """Calls the correct retriever method based on the legal sub-route."""
        k = DEFAULT_RETRIEVAL_K
        retrievers = {
            LEGAL_ROUTE_ORDER:      self._retriever.retrieve_order,
            LEGAL_ROUTE_GUIDELINE:  self._retriever.retrieve_guideline,
            LEGAL_ROUTE_STANDARD:   self._retriever.retrieve_standard,
            LEGAL_ROUTE_REGULATION: self._retriever.retrieve_regulation,
        }
        retrieve_fn = retrievers.get(route, self._retriever.retrieve_general)
        print(retrieve_fn)

        try:
            return await retrieve_fn(user_query=query, k=k, history=history)
        except Exception as e:
            logger.error(f"Retrieval failed for route={route}: {e}", exc_info=True)
            return [] 

    def _build_response(self, result: dict, retrieved_docs: list) -> RAGResponse:
        answer = result.get("answer_text", "ขออภัย ไม่พบข้อมูลที่เกี่ยวข้อง")
        refs_list = result.get("used_law_names", [])
        ref_dict = map_references_to_document_ids(retrieved_docs, refs_list)
        return RAGResponse(answer=answer, ref=ref_dict)

    @staticmethod
    def _parse_legal_route(decision: str) -> str:
        if LEGAL_ROUTE_STANDARD in decision:   return LEGAL_ROUTE_STANDARD
        if LEGAL_ROUTE_ORDER in decision:      return LEGAL_ROUTE_ORDER
        if LEGAL_ROUTE_GUIDELINE in decision:  return LEGAL_ROUTE_GUIDELINE
        if LEGAL_ROUTE_REGULATION in decision: return LEGAL_ROUTE_REGULATION
        return "GENERAL"