import asyncio
import logging
from typing import Any
from langchain_core.output_parsers import StrOutputParser
from src.app.chatbot.handlers.base import BaseHandler
from src.app.chatbot.schemas import RAGResponse
from src.app.chatbot.prompts.general import build_prompt

logger = logging.getLogger(__name__)

class GeneralHandler(BaseHandler):
    def __init__(self):
        self._prompt = build_prompt()   

    async def handle(self, query: str, history: list, llm: Any) -> RAGResponse:
        chain = (
            {
                "history": lambda x: history,
                "input": lambda x: query,
            }
            | self._prompt
            | llm
            | StrOutputParser()
        )
        try:
            answer = await self._invoke(chain, {})
            return RAGResponse(answer=answer, ref={})
        except asyncio.TimeoutError:
            logger.error("General timed out")
            return self._error_response()
        except Exception as e:
            logger.error(f"General failed: {e}", exc_info=True)
            return self._error_response()