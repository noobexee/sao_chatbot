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
    
    async def _get_routing_decision(self, query: str, history_messages: list) -> str: 
        history_str = "\n".join([f"{msg.type}: {msg.content}" for msg in history_messages[-3:]])

        routing_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a precision router for a Thai Legal RAG system.
            Classify the user's intent into exactly one category.

            ### PRIORITY RULES:
            1. **Primary Focus:** Analyze the 'Current Query' as the absolute truth for the user's current intent.
            2. **Secondary Context:** Use 'Conversation History' ONLY to understand pronouns (e.g., "it", "that file") or context if the current query is ambiguous.
            3. **Override:** If the 'Current Query' represents a clear shift in topic (e.g., switching from asking about laws to saying "Hello"), classify based on the new query, ignoring the previous legal context.

            ### CATEGORY DEFINITIONS:
            1. 'FILE_REQUEST':
            - The user explicitly asks for a physical file, a download link, or the full document.
            - Keywords (Thai): "ขอไฟล์" (request file), "ดาวน์โหลด" (download), "ฉบับเต็ม" (full version), "ขอ link", "PDF".
            - Example: "ขอไฟล์ ระเบียบสำนักงานตรวจเงินแผ่นดินหน่อย"

            2. 'LEGAL_RAG':
            - The user asks about the *content* of the law, procedures, definitions, penalties, or "how-to".
            - Keywords (Thai): "ทำอย่างไร" (how to), "คืออะไร" (what is), "ขั้นตอน" (procedure), "มีความผิดไหม" (is it illegal), "ประเมินความเสี่ยง" (risk assessment).
            - Example: "การคัดเลือกเรื่องที่มาจากการประเมินความเสี่ยงต้องทำอย่างไร"

            3. 'CHITCHAT':
            - Greetings, pleasantries, or off-topic non-legal conversation.
            - Example: "สวัสดี", "ขอบคุณครับ", "เก่งมาก"

            ### INSTRUCTION:
            Output ONLY the category name: CHITCHAT, FILE_REQUEST, or LEGAL_RAG. Do not explain."""),

            ("human", "Conversation History: {history}\n\nCurrent Query: {query}")
        ])
        
        chain = (
        {
            "history": lambda x: history_str, 
            "query": lambda x: query
        }
        | routing_prompt 
        | self.llm.get_model()
    )
        try:

            result = await chain.ainvoke({})
            
            decision = result.content.strip().upper()

            if "CHITCHAT" in decision: return "CHITCHAT"
            if "FILE_REQUEST" in decision: return "FILE_REQUEST"
            
            return "LEGAL_RAG"
        
        except Exception as e:
            print(f"Routing Chain Failed: {e}")
            return "LEGAL_RAG"

    async def _handle_chitchat(self, query: str, history: list):
        """
        Handles greetings and small talk. 
        Returns: (answer_text, [])
        """
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a helpful and polite Thai Legal Assistant. 
            Respond naturally to the user's greeting or small talk in Thai. 
            Do not provide legal advice or invent information."""),
            ("human", "{input}")
        ])
        
        chain = prompt | self.llm.get_model() | StrOutputParser()
        
        answer = await chain.ainvoke({"input": query})
        
        return answer, []

    async def _handle_legal_rag(self, query: str, history: list):
        retrieved_docs = await self.retriever.retrieve(query, history)
        
        prompt = ChatPromptTemplate.from_messages(
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
                ("human", "{query}")
            ]
        )

        chain = (
            {
                "context": lambda x: self._format_docs_with_sources(retrieved_docs),
                "history": lambda x: history,
                "query": lambda x: query
            }
            | prompt 
            | self.llm.get_model() 
            | StrOutputParser()
        )
        
        answer = await chain.ainvoke({})
        refs = list({doc.metadata.get("source", "Unknown") for doc in retrieved_docs})
        return answer, refs   
    
    async def _handle_file_request(self, query: str, histories: list):

        avaible_file = [] 
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", """
             You are a smart file librarian.
             
             Your Goal:
             1. Analyze the 'User Query' to see what file they want.
             2. Look at the 'Available Files' in the context.
             3. Extract the **exact filenames** (from the 'Filename' field) that match the user's request.
             4. If the file is not in the list, return an empty list for 'target_files'.
             5. Write a polite response in Thai (e.g., "here is the file you requested" or "sorry, I couldn't find that file").

             """),
            ("human", """
             Available Files:
             {context}

             User Query: {query}
             History : {history}
             """)
        ])
        
        chain = (
            {
                "context": lambda x: avaible_file,
                "query": lambda x: query,
                "history": lambda x: histories
            }
            | prompt 
            | self.llm.get_model() 
            | StrOutputParser()
        )
        
        answer = await chain.ainvoke({})
        return answer, answer

    async def answer_question(self, user_id: int, session_id: str, query: str) -> RAGResponse: 
        history_messages = self._get_history_objects(user_id, session_id)

        route = await self._get_routing_decision(query, history_messages)

        try:
            if route == "CHITCHAT":
                response_text, refs_data = await self._handle_chitchat(query, history_messages)
                
            elif route == "FILE_REQUEST":
                response_text, refs_data = await self._handle_file_request(query, history_messages)
                
            else:
                response_text, refs_data = await self._handle_legal_rag(query, history_messages)

        except Exception as e:
            print(f"Handler Failed: {e}")
            response_text = "ขออภัย ระบบเกิดข้อผิดพลาดในการประมวลผลคำตอบ"
            return RAGResponse(
                answer=response_text, 
                ref=refs_data 
            )    

        self.repository.save_message(user_id, session_id, query, response_text)

        return RAGResponse(
            answer=response_text, 
            ref=refs_data 
        )     

chatbot = Chatbot()