from typing import List, Any, Dict, Set, Optional
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser
from langchain_core.documents import Document
from src.app.llm.typhoon import TyphoonLLM
from src.app.chatbot.schemas import RAGResponse
from src.app.chatbot.retriever import Retriever
from src.db.repositories.chat_repository import ChatRepository
from langchain_core.globals import set_debug

set_debug(True)

class Chatbot:
    def __init__(self):
        self.llm = TyphoonLLM()
        self.repository = ChatRepository()
        self.retriever = Retriever()

    def _get_history_objects(self, user_id: int, session_id: str) -> List[Any]:
        rows = self.repository.get_messages_by_session(user_id, session_id)
        print(rows)
        messages = []
        for row in rows:
            if row[0]: messages.append(HumanMessage(content=row[0]))
            if row[1]: messages.append(AIMessage(content=row[1]))
        return messages

    def _format_docs_with_sources(self, docs: List[Document]) -> str:
        if not docs:
            return "No relevant legal documents found."
            
        formatted_chunks = []
        i = 1
        for doc in docs:
            formatted_chunks.append(f"Chunk {i} Title: {doc.metadata['law_name']} \n{doc.page_content}")
            i += 1
            
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

        prompt_template = ChatPromptTemplate.from_messages(
            [
                ("system", """
                    ### Role
                    You are a highly knowledgeable and professional Thai Legal Expert. Your goal is to provide accurate legal information based strictly on provided documentation while maintaining a professional and polite demeanor in Thai.

                    ### Variables
                    - **Context:** {context} (Information retrieved from the legal database)
                    - **Chat History:** {history} (Previous interactions for continuity)

                    ### Operational Logic & Constraints

                    1. **Query Classification:**
                    - **General Queries:** If the user's input is a greeting (e.g., "Hi", "Hello"), a common courtesy, or a non-legal request, respond naturally and professionally in Thai without using the context.
                    - **Legal Queries:** If the user asks about laws, regulations, or legal advice, you must analyze the provided context.

                    2. **Context Utilization (Strict RAG Rules):**
                    - You must prioritize the context for all legal answers.
                    - Because the retrieval system may include irrelevant data, you must evaluate the context first. If the context is irrelevant to the query or does not contain the answer, ignore it.
                    - **No Hallucination:** If the question is legal-related but the context does not provide the specific answer, you must clearly state that you do not have enough information to answer that specific question. Do not use external legal knowledge or make up answers.

                    3. **Response Style & Language:**
                    - **Language:** Always respond in **Professional Thai (ภาษาไทยระดับทางการ/กึ่งทางการ)**.
                    - **Tone:** Authoritative yet helpful and polite.
                    - **Conciseness:** Be direct and concise. Do not repeat the question or provide redundant explanations. Provide the core answer immediately.

                    4. **Interaction Handling:**
                    - Use the history to maintain context for follow-up questions (e.g., if the user asks "And what about the penalty for that?", refer to the previous topic in the history).

                    ### Formatting
                    - Use bullet points for lists of legal requirements or conditions.
                    - Use bold text for key legal terms or specific Section/Article numbers.
                
                    """),
                ("human", "{input}")
            ]
        )

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
            print(f"Chain Execution Failed: {e}")
            raise e

        self.repository.save_message(user_id, session_id, query, answer_text)
        
        model_name = getattr(llm_runnable, "model_name", getattr(llm_runnable, "model", "Unknown Model"))
        refs_data = list({doc.metadata.get("source", "Unknown") for doc in retrieved_docs})

        return RAGResponse(
            answer=answer_text, 
            model_used=model_name, 
            ref=refs_data 
        )     

chatbot = Chatbot()