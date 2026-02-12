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
            ("system", """You are a precision router for the State Audit Office (สตง.) Thai Legal RAG.
            Your job is to distinguish between asking ABOUT the law vs. asking HOW TO CONTACT the office.

            ### CATEGORIES:
            1. 'FAQ': 
               - Focus: Logistics, Contact, Location, Phone numbers.
               - Intent: The user wants to reach a human, find an office, or know opening hours.
               - Example: "ติดต่อ สตง ยังไง", "ขอเบอร์โทรหน่อย", "สำนักงานเปิดกี่โมง"
            
            2. 'FILE_REQUEST':
               - Focus: Downloading documents.
               - Intent: Wants a PDF, Link, or Full Paper.
               - Example: "ขอไฟล์ระเบียบ", "โหลด PDF ตรงไหน"

            3. 'LEGAL_RAG':
               - Focus: Law substance, audit rules, "Is this legal?", "How to audit?".
               - Intent: The user is asking for legal/procedural knowledge.
               - Example: "การประเมินความเสี่ยงทำอย่างไร", "ผิดวินัยการเงินไหม"

            4. 'CHITCHAT':
               - Focus: Greetings and thanks.

            ### CRITICAL LOGIC OVERRIDE:
            - IF the query contains "ติดต่อ" (Contact) or "เบอร์โทร" (Phone), it is ALWAYS 'FAQ'.
            - DO NOT classify "How to contact" as 'LEGAL_RAG' even if it mentions the office name (สตง).
            - 'LEGAL_RAG' is ONLY for laws, rules, and audit technicalities.

            ### EXAMPLES:
            - "ถ้าต้องการติดต่อ สตง. ต้องทำอย่างไร" -> FAQ
            - "เบอร์โทร สตง. เบอร์อะไร" -> FAQ
            - "ขอระเบียบการพัสดุฉบับเต็ม" -> FILE_REQUEST
            - "ขั้นตอนการตรวจเงินแผ่นดิน" -> LEGAL_RAG

            Output ONLY the category name: FAQ, FILE_REQUEST, LEGAL_RAG, or CHITCHAT."""),

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
            if "FAQ" in decision: return "FAQ"
            
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
            ### ROLE
            You are a specialized assistant for a Thai Legal RAG system.
            **YOUR AUTHORITY IS LIMITED TO THE PROVIDED CONTEXT ONLY.**
            You are FORBIDDEN from using your internal training data, external websites, or general knowledge to answer questions.

            ### DATA SOURCES
            - **Context:** {context}
            - **Chat History:** {history}

            ### STRICT OPERATIONAL RULES (MUST FOLLOW):
            1. **NO OUTSIDE KNOWLEDGE:** - If the answer is not explicitly written in the **Context** above, you MUST say you do not have the information.
               - **DO NOT** invent, guess, or provide phone numbers, websites, or addresses unless they are physically present in the **Context** text.
               - **DO NOT** try to be "helpful" by providing general contact info for government offices (e.g., OAG/สตง.) if it is not in the documents.

            2. **CHECK FOR RELEVANCE:**
               - The user might ask a "How-to" question (e.g., "How to contact"). 
               - If the **Context** contains legal procedures (e.g., "How to audit") but NOT contact info, **YOU MUST REFUSE TO ANSWER.** - Do not twist a legal procedure to fit a contact question.

            3. **RESPONSE FORMAT:**
               - Answer in **Professional Thai (ภาษาไทยระดับทางการ)**.
               - Be direct and concise.
               - Use **bold** for important legal terms or section numbers (e.g., **มาตรา 42**).

            ### MANDATORY REFUSAL MESSAGE
            If the **Context** does not contain the answer, or if the retrieved documents are irrelevant to the user's specific question, output EXACTLY this message:
            "ขออภัยครับ เอกสารที่สืบค้นได้ไม่ครอบคลุมข้อมูลในส่วนนี้ (เช่น ข้อมูลติดต่อ หรือระเบียบที่ท่านถามถึง) ผมจึงไม่สามารถให้คำตอบที่ถูกต้องตามเอกสารอ้างอิงได้ครับ"
            """),
            
            ("human", """
            Context: {context}
            User Query: {query}
            """)
        ])


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

    async def _handle_FAQ(self, query: str, history: list):

        return "ขออภัยครับ ผมไม่มีข้อมูลในส่วนนี้ (ข้อมูลติดต่อหรือที่อยู่หน่วยงาน) ผมสามารถให้ข้อมูลได้เฉพาะเรื่องกฎหมายและระเบียบการตรวจสอบเท่านั้นครับ", []


    async def answer_question(self, user_id: int, session_id: str, query: str) -> RAGResponse: 
        history_messages = self._get_history_objects(user_id, session_id)

        route = await self._get_routing_decision(query, history_messages)

        try:
            if route == "CHITCHAT":
                response_text, refs_data = await self._handle_chitchat(query, history_messages)
                
            elif route == "FILE_REQUEST":
                response_text, refs_data = await self._handle_file_request(query, history_messages)

            elif route == "FAQ":
                response_text, refs_data = await self._handle_FAQ(query, history_messages)
                
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


