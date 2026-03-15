import logging
from typing import Any
from src.app.chatbot.retriever import Retriever
from src.app.chatbot.router import get_top_level_route
from src.app.chatbot.schemas import RAGResponse
from src.app.llm.llm_manager import get_llm
from src.db.repositories.chat_repository import ChatRepository
from src.db.repositories.document_repository import DocumentRepository
from langchain_core.messages import HumanMessage, AIMessage

from src.app.chatbot.constants import (
    ROUTE_GENERAL,
    ROUTE_FILE_REQUEST,
    ROUTE_LEGAL_QUERY,
)
from src.app.chatbot.handlers import (
    GeneralHandler,
    FileRequestHandler,
    LegalRagHandler,
    BaseHandler
)

logger = logging.getLogger(__name__)

class Chatbot:

    def __init__(self):
        self._llm = get_llm().get_model()
        self._repository = ChatRepository()
        self._retriever = Retriever()

        self._handlers: dict[str, BaseHandler] = {
            ROUTE_GENERAL:     GeneralHandler(),
            ROUTE_FILE_REQUEST: FileRequestHandler(repository=DocumentRepository()),
            ROUTE_LEGAL_QUERY:    LegalRagHandler(retriever=self._retriever),
        }

    async def answer_question(
        self, user_id: str, session_id: str, query: str
    ) -> RAGResponse:
        log_prefix = f"[{user_id}|{session_id}]"
        logger.info(f"{log_prefix} query: {query[:80]}")

        history = self._load_history(user_id, session_id)
        route = await get_top_level_route(query, history, self._llm)
        logger.info(f"{log_prefix} route: {route}")

        result = await self._handlers[route].handle(query, history, self._llm)

        self._save_message(user_id, session_id, query, result)

        return result

    def get_session_history(
        self, user_id: str, session_id: str
    ) -> list[dict]:
        try:
            rows = self._repository.get_messages_by_session(user_id, session_id)
            history = []
            for row in rows:
                timestamp = row[2].isoformat() if row[2] else ""
                if row[0]:
                    history.append({
                        "role": "user",
                        "content": row[0],
                        "created_at": timestamp,
                    })
                if row[1]:
                    history.append({
                        "role": "assistant",
                        "content": row[1],
                        "created_at": timestamp,
                        "references": row[3] if len(row) > 3 else [],
                    })
            return history
        except Exception as e:
            logger.warning(f"get_session_history failed: {e}")
            return []

    def get_user_sessions(self, user_id: str) -> list[dict]:
        try:
            return self._repository.get_user_sessions_summary(user_id)
        except Exception as e:
            logger.warning(f"get_user_sessions failed for {user_id}: {e}")
            return []

    def delete_session_history(
        self, user_id: str, session_id: str
    ) -> dict[str, Any]:
        try:
            success = self._repository.delete_session(user_id, session_id)
            if success:
                return {
                    "status": "success",
                    "message": f"Session {session_id} deleted successfully.",
                }
            return {
                "status": "error",
                "message": "Failed to delete session from database.",
            }
        except Exception as e:
            logger.error(f"delete_session_history failed: {e}", exc_info=True)
            return {"status": "error", "message": str(e)}

    def update_session(
        self,
        user_id: str,
        session_id: str,
        title: str | None = None,
        is_pinned: bool | None = None,
    ) -> dict[str, Any]:
        try:
            success = self._repository.update_session_metadata(
                user_id, session_id, title, is_pinned
            )
            if success:
                return {"status": "success", "message": "Session updated successfully."}
            return {"status": "error", "message": "Failed to update session."}
        except Exception as e:
            logger.error(f"update_session failed: {e}", exc_info=True)
            return {"status": "error", "message": str(e)}

    def _load_history(self, user_id: str, session_id: str) -> list:
        """
        Loads chat history from the repository and returns
        LangChain message objects for prompt injection.
        """
        try:
            rows = self._repository.get_messages_by_session(user_id, session_id)
            messages = []
            for row in rows:
                if row[0]:
                    messages.append(HumanMessage(content=row[0]))
                if row[1]:
                    messages.append(AIMessage(content=row[1]))
            return messages
        except Exception as e:
            logger.warning(
                f"_load_history failed for session {session_id}, "
                f"proceeding with empty history: {e}"
            )
            return []

    def _save_message(
        self,
        user_id: str,
        session_id: str,
        query: str,
        result: RAGResponse,
    ) -> None:
        """
        Persists the exchange to the database.
        Failure is logged but never raised — a DB error should not
        """
        try:
            self._repository.save_message(
                user_id,
                session_id,
                query,
                result.answer,
                refs=result.ref,
            )
        except Exception as e:
            logger.error(f"_save_message failed: {e}", exc_info=True)


chatbot = Chatbot()