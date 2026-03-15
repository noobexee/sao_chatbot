import asyncio
import logging
from typing import Any
from langchain_core.output_parsers import JsonOutputParser
from src.app.chatbot.handlers.base import BaseHandler
from src.app.chatbot.prompts.file_request import build_prompt
from src.app.chatbot.schemas import RAGResponse, FileResponseSchema
from src.app.chatbot.constants import HISTORY_WINDOW
from src.db.repositories.document_repository import DocumentRepository

logger = logging.getLogger(__name__)

class FileRequestHandler(BaseHandler):

    _error_message = "ขออภัยครับ เกิดข้อผิดพลาดในการค้นหาไฟล์ของระบบ"

    def __init__(self, repository: DocumentRepository):
        self._repository = repository
        self._prompt = build_prompt()
        self._parser = JsonOutputParser(pydantic_object=FileResponseSchema)

    async def handle(self, query: str, history: list, llm: Any) -> RAGResponse:
        available_documents = await self._fetch_documents()
        if available_documents is None:
            return self._error_response("ขออภัยครับ ไม่สามารถเชื่อมต่อฐานข้อมูลได้ในขณะนี้")

        if not available_documents:
            return self._error_response("ระบบยังไม่มีไฟล์เอกสารในขณะนี้ครับ")

        title_to_id = {
            doc["title"]: doc["id"]
            for doc in available_documents
            if doc.get("title") and doc.get("id")
        }

        context = self._build_context(title_to_id)
        history_str = self._format_history(history, window=HISTORY_WINDOW)

        chain = (
            {
                "context":             lambda x: context,
                "query":               lambda x: query,
                "history":             lambda x: history_str,
                "format_instructions": lambda x: self._parser.get_format_instructions(),
            }
            | self._prompt
            | llm
            | self._parser
        )

        try:
            result = await self._invoke(chain, {})
            return self._build_response(result, title_to_id)
        except asyncio.TimeoutError:
            logger.error("FileRequestHandler timed out")
            return self._error_response()
        except Exception as e:
            logger.error(f"FileRequestHandler failed: {e}", exc_info=True)
            return self._error_response()


    async def _fetch_documents(self) -> list | None:
        """
        Returns document list on success, None on DB error
        """
        try:
            return await asyncio.to_thread(self._repository.list_documents)
        except Exception as e:
            logger.error(f"Document fetch failed: {e}", exc_info=True)
            return None

    def _build_context(self, title_to_id: dict) -> str:
        """
        Formats all available document titles into a bullet list for the LLM
        """
        return "\n".join(f"- {title}" for title in title_to_id.keys())

    def _build_response(self, result: dict, title_to_id: dict) -> RAGResponse:
        """Maps LLM-returned filenames back to their document IDs"""
        ref_dict = {
            title: title_to_id[title]
            for title in result.get("target_files", [])
            if title in title_to_id
        }
        return RAGResponse(
            answer=result.get("answer_text", ""),
            ref=ref_dict,
        )