import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Any

from src.app.chatbot.schemas import RAGResponse
from src.app.chatbot.constants import LLM_TIMEOUT_SECONDS

logger = logging.getLogger(__name__)

class BaseHandler(ABC):
    _error_message = "ขออภัย ระบบขัดข้องชั่วคราว กรุณาลองใหม่อีกครั้งในภายหลัง"

    @abstractmethod
    async def handle(self, query: str, history: list, llm: Any) -> RAGResponse:
        """Every handler must implement this."""

    async def _invoke(self, chain, inputs: dict) -> Any:
        return await asyncio.wait_for(
            chain.ainvoke(inputs),
            timeout=LLM_TIMEOUT_SECONDS,
        )

    def _error_response(self, message: str | None = None) -> RAGResponse:
        return RAGResponse(answer=message or self._error_message, ref={})

    def _format_history(self, history: list, window: int) -> str:
        """
        Truncate and serialize history for prompt injection.
        Caps each message at 500 chars to avoid blowing the context window.
        """
        if not history:
            return "No history."
        return "\n".join(
            f"{msg.type}: {msg.content[:500]}"
            for msg in history[-window:]
        )