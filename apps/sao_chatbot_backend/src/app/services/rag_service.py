from typing import List, Any, Dict, Set, Optional
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser
from langchain_core.documents import Document
from src.app.services.models.rag_response import RAGResponse
from .llm_manager import get_llm
from src.db.repositories.chat_repository import ChatRepository
from src.db.vector_store import get_vectorstore

class RAGService:
    def __init__(self):
        self.llm = get_llm()
        self.repository = ChatRepository()
        
        self.vectorstore = get_vectorstore()
        self.retriever = self.vectorstore.as_retriever(search_kwargs={"k": 4})

    def _get_history_objects(self, user_id: int, session_id: str) -> List[Any]:
        rows = self.repository.get_messages_by_session(user_id, session_id)
        messages = []
        for row in rows:
            if row[0]: 
                messages.append(HumanMessage(content=row[0]))
            if row[1]: 
                messages.append(AIMessage(content=row[1]))
        return messages

    def _format_docs_with_sources(self, docs: List[Document]) -> str:
        formatted_chunks = []
        for doc in docs:
            full_path = doc.metadata.get("source", "Unknown File")
            file_name = full_path.split("/")[-1]
            page = doc.metadata.get("page", 1) 
            
            chunk_str = f"[Source: {file_name}, Page: {page}]\n{doc.page_content}"
            formatted_chunks.append(chunk_str)
        
        return "\n\n---\n\n".join(formatted_chunks)

    async def answer_question(self, user_id: int, session_id: str, query: str) -> RAGResponse: 
        history_messages = self._get_history_objects(user_id, session_id)
        llm_runnable = self.llm.get_model()

        retrieved_docs = await self.retriever.ainvoke(query)
        print(f"\n🔍 Query: {query}")
        print(f"🔍 Found {len(retrieved_docs)} chunks:")
        for i, doc in enumerate(retrieved_docs):
            print(f"--- Chunk {i+1} (Page {doc.metadata.get('page')}) ---")
            print(doc.page_content[:200].replace('\n', ' '))
        
        prompt_template = ChatPromptTemplate.from_messages([
            ("system", """คุณเป็นผู้ช่วยทางกฎหมายที่เชี่ยวชาญระเบียบสำนักงานตรวจเงินแผ่นดิน
            จงตอบคำถามโดยใช้ข้อมูลจาก Context ที่ให้มาเท่านั้น
            
            รูปแบบการตอบ (Format):
            1. เริ่มต้นด้วย "ตอบ :" ตามด้วยคำตอบที่คุณสรุปมา
            2. จบด้วย "อ้างอิง :" ตามด้วยข้อความจริงจากกฎหมาย (ตัวบท) ที่คุณนำมาใช้อ้างอิง (ระบุเลขข้อถ้ามี)
            
            Context:
            {context}"""),
            MessagesPlaceholder(variable_name="history"), 
            ("human", "{input}")
        ])

        chain = (
            {
                "context": lambda x: self._format_docs_with_sources(retrieved_docs),
                "history": lambda x: history_messages,
                "input": lambda x: query
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
            

        self.repository.save_message(user_id, session_id, query, answer_text)
        
        model_name = getattr(llm_runnable, "model_name", getattr(llm_runnable, "model", "Unknown Model"))

        refs_data = []
        seen_files = set()
        
        for doc in retrieved_docs:
            full_path = doc.metadata.get("source", "Unknown")
            file_name = full_path.split("/")[-1]
            
            if file_name not in seen_files:
                refs_data.append(file_name) 
                seen_files.add(file_name)
        return RAGResponse(
            answer=answer_text, 
            model_used=model_name, 
            ref=refs_data 
        )

    def get_session_history(self, user_id: int, session_id: str) -> List[Dict]:
        rows = self.repository.get_messages_by_session(user_id, session_id)
        formatted_history = []
        for row in rows:
            timestamp = row[2].isoformat() if row[2] else ""
            formatted_history.append({"role": "user", "content": row[0], "created_at": timestamp})
            formatted_history.append({"role": "assistant", "content": row[1], "created_at": timestamp})
        return formatted_history

    def get_user_sessions(self, user_id: int) -> List[Dict]:
        # This calls the updated repository method that returns {session_id, title, is_pinned...}
        return self.repository.get_user_sessions_summary(user_id)

    # --- DELETE METHOD ---
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

    # --- UPDATE METHOD (Rename / Pin) ---
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

rag_service = RAGService()