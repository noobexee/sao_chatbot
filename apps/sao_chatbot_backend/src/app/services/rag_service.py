from typing import List, Any, Dict
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser
from src.api.v1.models.rag_response import RAGResponse
from src.app.services.llm_manager import get_llm
from src.db.repositories.chat_repository import ChatRepository

class RAGService:
    def __init__(self):
        self.llm = get_llm()
        self.repository = ChatRepository() 

    def _get_history_objects(self, user_id: int, session_id: str) -> List[Any]:
        """
        Converts raw DB rows -> LangChain Message Objects
        """
        rows = self.repository.get_messages_by_session(user_id, session_id)
        
        messages = []
        for row in rows:
            if row[0]:
                messages.append(HumanMessage(content=row[0]))
            if row[1]:
                messages.append(AIMessage(content=row[1]))
        
        return messages

    def get_session_history(self, user_id: int, session_id: str) -> List[Dict]:
        """
        Converts raw DB rows -> Frontend JSON format
        """
        rows = self.repository.get_messages_by_session(user_id, session_id)
        
        formatted_history = []
        for row in rows:
            timestamp = row[2].isoformat() if row[2] else ""
            formatted_history.append({"role": "user", "content": row[0], "created_at": timestamp})
            formatted_history.append({"role": "assistant", "content": row[1], "created_at": timestamp})
            
        return formatted_history

    def get_user_sessions(self, user_id: int) -> List[Dict]:
        """
        Converts raw DB rows -> Sidebar JSON format
        """
        rows = self.repository.get_user_sessions_summary(user_id)
        
        sessions = []
        for row in rows:
            title = row[1]
            display_title = title[:50] + "..." if len(title) > 50 else title
            
            sessions.append({
                "session_id": str(row[0]),
                "title": display_title,
                "created_at": row[2].isoformat()
            })
            
        sessions.sort(key=lambda x: x['created_at'], reverse=True)
        return sessions

    async def answer_question(self, user_id: int, session_id: str, query: str) -> RAGResponse:
        history_messages = self._get_history_objects(user_id, session_id)

        prompt_template = ChatPromptTemplate.from_messages([
            ("system", "You are a helpful assistant."),
            MessagesPlaceholder(variable_name="history"), 
            ("human", "{input}")
        ])

        llm_runnable = self.llm.get_model()
        chain = prompt_template | llm_runnable | StrOutputParser()

        try:
            answer_text = await chain.ainvoke({
                "history": history_messages,
                "input": query
            })
        except Exception:
            answer_text = chain.invoke({
                "history": history_messages,
                "input": query
            })

        self.repository.save_message(user_id, session_id, query, answer_text)

        model_name = getattr(llm_runnable, "model_name", getattr(llm_runnable, "model", "Unknown Model"))

        return RAGResponse(answer=answer_text, model_used=model_name)

rag_service = RAGService()