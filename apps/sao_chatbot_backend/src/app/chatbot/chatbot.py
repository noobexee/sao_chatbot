from typing import List, Any, Dict, Optional
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from src.app.llm.llm_manager import get_llm
from src.app.chatbot.schemas import RAGResponse
from src.app.chatbot.retriever import Retriever
from src.db.repositories.chat_repository import ChatRepository
from .route_handlers import handle_chitchat, handle_file_request, handle_FAQ, handle_legal_rag, get_legal_route
import logging
from langchain_core.globals import set_debug

logger = logging.getLogger(__name__)
    
class Chatbot:
    def __init__(self):
        self.llm_service = get_llm() 
        self.llm = self.llm_service.get_model()
        self.repository = ChatRepository()
        self.retriever = Retriever()

    def _get_history_objects(self, user_id: str, session_id: str) -> List[Any]:
        try:
            rows = self.repository.get_messages_by_session(user_id, session_id)
            messages = []
            for row in rows:
                if row[0]: messages.append(HumanMessage(content=row[0]))
                if row[1]: messages.append(AIMessage(content=row[1]))
            return messages
        except Exception as e:
            logger.warning(f"Session history retrieval failed for {session_id}. Proceeding with empty history.")
            return []
 
    def get_session_history(self, user_id: str, session_id: str) -> List[Dict]:
        try :
            rows = self.repository.get_messages_by_session(user_id, session_id)
            formatted_history = []
            for row in rows:
                timestamp = row[2].isoformat() if row[2] else ""
                
                formatted_history.append({"role": "user", "content": row[0], "created_at": timestamp})
                
                formatted_history.append({
                    "role": "assistant", 
                    "content": row[1], 
                    "created_at": timestamp,
                    "references": row[3] if len(row) > 3 else [] 
                })
            return formatted_history
        except Exception as e:
            logger.warning(f"Session history retrieval failed: {e}")
            return []

    def get_user_sessions(self, user_id: str) -> List[Dict]:
        try : 
            return self.repository.get_user_sessions_summary(user_id)
        except Exception as e:
            logger.warning(f"Session retrieval failed for {user_id}. Proceeding with empty history.")
            return []

    def delete_session_history(self, user_id: str, session_id: str) -> Dict[str, Any]:
        try:
            success = self.repository.delete_session(user_id, session_id)
            if success:
                return {"status": "success", "message": f"Session {session_id} deleted successfully."}
            else:
                return {"status": "error", "message": "Failed to delete session from database."}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def update_session(self, user_id: str, session_id: str, title: Optional[str] = None, is_pinned: Optional[bool] = None) -> Dict[str, Any]:
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
        | self.llm
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

    async def answer_question(self, user_id: str, session_id: str, query: str) -> RAGResponse: 
        log_prefix = f"[User: {user_id} | Session: {session_id}]"
        try:
            logger.info(f"{log_prefix} Received query: {query[:50]}...")
            history_messages = self._get_history_objects(user_id, session_id)
            route = await self._get_routing_decision(query, history_messages)
            logger.info(f"{log_prefix} Routed to: {route}")

            handlers = {
                "CHITCHAT": handle_chitchat,
                "FILE_REQUEST": handle_file_request,
                "FAQ": handle_FAQ,
                "LEGAL_RAG": lambda q, h, m: handle_legal_rag(q, h, m, self.retriever)
            }
            
            handler = handlers.get(route, handlers["LEGAL_RAG"])
            result = await handler(query, history_messages, self.llm)
            response_text = result.answer
            refs_data = result.ref

            try:
                self.repository.save_message(
                    user_id, 
                    session_id, 
                    query, 
                    response_text, 
                    refs=refs_data
                )
            except Exception as db_err:
                logger.error(f"Database save failed: {db_err}")

            return RAGResponse(answer=response_text, ref=refs_data)

        except Exception as e:
            logger.error(f"{log_prefix} Failed to process: {e}", exc_info=True)
            return RAGResponse(
                answer="ขออภัย ระบบขัดข้องชั่วคราว กรุณาลองใหม่อีกครั้งในภายหลัง",
                ref={}
            )  

chatbot = Chatbot()


