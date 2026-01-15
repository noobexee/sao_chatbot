from typing import List, Any, Dict, Set, Optional
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser
from langchain_core.documents import Document
from src.app.llm.typhoon import TyphoonLLM
from src.app.chatbot.schemas import RAGResponse
from src.app.chatbot.retriever import Retriever
from src.db.repositories.chat_repository import ChatRepository

class Chatbot:
    def __init__(self):
        self.llm = TyphoonLLM().get_model()
        self.repository = ChatRepository()
        self.retriever = Retriever()

    def _get_history_objects(self, user_id: int, session_id: str) -> List[Any]:
        rows = self.repository.get_messages_by_session(user_id, session_id)
        messages = []
        for row in rows:
            if row[0]: messages.append(HumanMessage(content=row[0]))
            if row[1]: messages.append(AIMessage(content=row[1]))
        return messages

    def _format_docs_with_sources(self, docs: List[Document]) -> str:
        if not docs:
            return "No relevant legal documents found."
            
        formatted_chunks = []
        for doc in docs:
            file_name = doc.metadata.get("source", "Unknown File").split("/")[-1]
            para = doc.metadata.get("paragraph_number", "?")
            formatted_chunks.append(f"[Source: {file_name}, Para: {para}]\n{doc.page_content}")
            
        return "\n\n---\n\n".join(formatted_chunks)
    
    def get_session_history(self, user_id: int, session_id: str) -> List[Dict]:
        rows = self.repository.get_messages_by_session(user_id, session_id)
        formatted_history = []
        for row in rows:
            timestamp = row[2].isoformat() if row[2] else ""
            formatted_history.append({"role": "user", "content": row[0], "created_at": timestamp})
            formatted_history.append({"role": "assistant", "content": row[1], "created_at": timestamp})
        return formatted_history

    def get_user_sessions(self, user_id: int) -> List[Dict]:
        return self.repository.get_user_sessions_summary(user_id)

    def delete_session_history(self, user_id: int, session_id: str) -> Dict[str, Any]:
        """
        Deletes a specific chat session.
        """
        try:
            success = self.repository.delete_session(user_id, session_id)
            if success:
                return {"status": "success", "message": f"Session {session_id} deleted successfully."}
            else:
                return {"status": "error", "message": "Failed to delete session from database."}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def update_session(self, user_id: int, session_id: str, title: Optional[str] = None, is_pinned: Optional[bool] = None) -> Dict[str, Any]:
        """
        Updates session metadata (title, pinned status).
        """
        try:
            success = self.repository.update_session_metadata(user_id, session_id, title, is_pinned)
            
            if success:
                return {"status": "success", "message": "Session updated successfully."}
            else:
                return {"status": "error", "message": "Failed to update session in database."}
        except AttributeError:
             return {"status": "error", "message": "Repository method 'update_session_metadata' not found."}
        except Exception as e:
            return {"status": "error", "message": str(e)}
        
    async def answer_question(self, user_id: int, session_id: str, query: str) -> RAGResponse: 
        history_messages = self._get_history_objects(user_id, session_id)
        llm_runnable = self.llm.get_model()

        retrieved_docs = await self.retriever.retrieve(query, history_messages)
        
        analysis_date_info = retrieved_docs[0].metadata.get("_analysis_date", "Unknown") if retrieved_docs else "Unknown"

        prompt_template = ChatPromptTemplate.from_messages([
            ("system", """คุณเป็นผู้ช่วยทางกฎหมายที่เชี่ยวชาญระเบียบสำนักงานตรวจเงินแผ่นดิน
            จงตอบคำถามโดยใช้ข้อมูลจาก Context ที่ให้มาเท่านั้น
            เนื้อหาด้านล่างนี้สะท้อนถึงกฎหมายที่ใช้บังคับ ณ วันที่: {{analysis_date}}
            Context:
            {context}"""),
            MessagesPlaceholder(variable_name="history"), 
            ("human", "{input}")
        ])

        chain = (
            {
                "context": lambda x: self._format_docs_with_sources(retrieved_docs),
                "history": lambda x: history_messages,
                "input": lambda x: query,
                "analysis_date": lambda x: analysis_date_info
            }
            | prompt_template 
            | llm_runnable 
            | StrOutputParser()
        ) 

        try:
            answer_text = await chain.ainvoke({})
        except Exception as e:
            print(f"❌ Chain Execution Failed: {e}")
            raise e

        # 3. SAVE & RETURN
        self.repository.save_message(user_id, session_id, query, answer_text)
        
        model_name = getattr(llm_runnable, "model_name", getattr(llm_runnable, "model", "Unknown Model"))
        refs_data = list({doc.metadata.get("source", "Unknown") for doc in retrieved_docs})

        return RAGResponse(
            answer=answer_text, 
            model_used=model_name, 
            ref=refs_data 
        )     
chatbot = Chatbot()