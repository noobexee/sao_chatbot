from typing import List, Any, Dict, Optional
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser
from langchain_core.documents import Document
from pydantic import BaseModel, Field
from langchain_core.output_parsers import JsonOutputParser
from src.app.llm.typhoon import TyphoonLLM
from src.app.chatbot.schemas import RAGResponse
from src.app.chatbot.retriever import Retriever
from src.db.repositories.chat_repository import ChatRepository
from langchain_core.globals import set_debug

set_debug(True)
class FileResponse(BaseModel):
    answer_text: str = Field(description="A polite, formal Thai response (e.g., 'ขออนุญาตนำส่งเอกสาร').")
    target_files: List[str] = Field(description="List of exact filenames found. Empty list if none.")
    
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
            formatted_chunks.append(f"Chunk {i} Title: {doc.get('law_name')} \n{doc.get('text')}")
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
        history_str = "\n".join([f"{msg.type}: {msg.content}" for msg in history_messages[-5:]])

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

        prompt = ChatPromptTemplate.from_messages([
            ("system", """
                You are a specialized Legal Assistant skilled in the regulations of the **Office of the Ombudsman (สำนักงานผู้ตรวจการแผ่นดิน)**.
                
                **Your Scope of Expertise:**
                1. **Regulations (ระเบียบ):** Official regulations of the Office of the Ombudsman.
                2. **Orders (คำสั่ง):** Administrative or enforcement orders related to the office.
                3. **Guidelines (แนวทาง):** Operational guidelines and practice standards.

                **Your Goal:** Politely acknowledge the user's greeting, then immediately guide them to ask about these specific documents.
                
                **Guidelines:**
                - **Language:** Professional Thai (ภาษาไทยระดับทางการ).
                - **Tone:** Formal, precise, and helpful.
                - **Pivot Strategy:** Do not stay in small talk. End your greeting by listing what you can search for (Regulations, Orders, Guidelines).
                
                **Example Response:**
                - User: "สวัสดี" (Hello)
                - You: "สวัสดีครับ ผมเป็นระบบผู้ช่วยค้นหาข้อมูลระเบียบ คำสั่ง และแนวทางปฏิบัติของสำนักงานผู้ตรวจการแผ่นดิน มีหัวข้อใดที่ต้องการให้ช่วยตรวจสอบไหมครับ"
            """
            ),
            MessagesPlaceholder(variable_name="history"),
            ("human", "{input}")
        ])
        chain = (
            {
                "history": lambda x: history,
                "input": lambda x: query
            }
            | prompt 
            | self.llm.get_model() 
            | StrOutputParser()
        )
        
        answer = await chain.ainvoke({"input": query})
        
        return answer, []

    async def _handle_legal_rag(self, query: str, history: list):
        retrieved_docs = await self.retriever.retrieve(query, history)
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", """
                ### Role
                You are a highly knowledgeable and professional Thai Legal Expert. Your goal is to provide accurate legal information based strictly on provided documentation while maintaining a professional and polite demeanor in Thai.

                ### Variables
                - **Context:** {context} (Information retrieved from the legal database)
                - **Chat History:** {history} (Previous interactions for continuity)

                ### Operational Logic & Constraints

                1. **Query Classification:**
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
                
                ### Mandatory Refusal
                If the query cannot be answered by the context, respond: "ขออภัยครับ ข้อมูลในเอกสารที่ได้รับมาไม่ครอบคลุมประเด็นนี้ ผมจึงไม่สามารถให้คำตอบที่ถูกต้องตามกฎหมายได้"
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
        refs = list({doc.get("law_name") for doc in retrieved_docs})
        return answer, refs   
    
    async def _handle_file_request(self, query: str, history: list):
        parser = JsonOutputParser(pydantic_object=FileResponse)
        
        available_files_list = [
            "แนวทางการปฏิบัติงาน_SAO.pdf",
            "ระเบียบการเบิกจ่าย_2567.pdf"
        ]
        files_context = "\n".join(available_files_list)

        prompt = ChatPromptTemplate.from_messages([
            ("system", """
            You are a smart "File Librarian" for the Office of the Ombudsman.
            Respond in Formal Thai.
            {format_instructions}
            """),
            ("human", """
            Available Files:
            {context}

            User Query: {query}
            History: {history}
            """),
        ])
        chain = (
            {
                    "context": lambda x: files_context,
                    "query": lambda x: query,
                    "history": lambda x: history,
                    "format_instructions": lambda x: parser.get_format_instructions()
            }
                | prompt 
                | self.llm.get_model() 
                | parser
        )
    
        try:
            response = await chain.ainvoke({})
            return response["answer_text"], response["target_files"]
                
        except Exception as e:
            print(f"Error parsing JSON: {e}")
            return "ขออภัยครับ เกิดข้อผิดพลาดในการค้นหาไฟล์", []    
        
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


