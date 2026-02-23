from typing import List, Any, Dict, Optional
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser
from pydantic import BaseModel, Field
from langchain_core.output_parsers import JsonOutputParser
from src.app.chatbot.retriever import Retriever
from .utils.formatters import format_regulation_context


class LegalResponseSchema(BaseModel):
    answer_text: str = Field(description="The natural Thai response starting with 'จากข้อ... ของระเบียบ...'")
    used_law_names: List[str] = Field(description="List of exact law_names or guideline_names from the context that were used to answer the question.")

class FileResponse(BaseModel):
    answer_text: str = Field(description="A polite, formal Thai response (e.g., 'ขออนุญาตนำส่งเอกสาร').")
    target_files: List[str] = Field(description="List of exact filenames found. Empty list if none.")

async def handle_chitchat(query: str, history: list, llm):

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
        | llm 
        | StrOutputParser()
    )
    
    answer = await chain.ainvoke({"input": query})
    
    return answer, []

async def handle_file_request(query: str, history: list, llm: Any):
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
            | llm
            | parser
    )

    try:
        response = await chain.ainvoke({})
        return response["answer_text"], response["target_files"]
            
    except Exception as e:
        print(f"Error parsing JSON: {e}")
        return "ขออภัยครับ เกิดข้อผิดพลาดในการค้นหาไฟล์", []    


async def handle_FAQ(query: str, history: list, llm:Any):

    return "ขออภัยครับ ผมไม่มีข้อมูลในส่วนนี้ (ข้อมูลติดต่อหรือที่อยู่หน่วยงาน) ผมสามารถให้ข้อมูลได้เฉพาะเรื่องกฎหมายและระเบียบการตรวจสอบเท่านั้นครับ", []

async def get_legal_route(query: str, history_messages: list, llm: Any) -> str:

    history_str = "\n".join([f"{msg.type}: {msg.content}" for msg in history_messages[-3:]]) if history_messages else "No history."

    routing_prompt = ChatPromptTemplate.from_messages([
        ("system", """You are an intelligent legal router for the State Audit Office (สตง.) Thai Legal RAG.
        Classify the query into: REGULATION, ORDER, GUIDELINE, STANDARD, or GENERAL.

        ### CRITICAL PARSING RULE:
        Focus on the ACTUAL QUESTION being asked (usually at the end of the sentence). 
        Distinguish between the "Topic" (what they are talking about) and the "Core Question" (what they want to know).
        Your routing decision MUST be based on the Core Question.

        ### ROUTING RULES & CRITICAL EXCEPTIONS:

        1. 'STANDARD'
           - TRIGGER: The query contains "หลักเกณฑ์มาตรฐาน" or "หลักเกณฑ์มาตรฐานการตรวจสอบ".

        2. 'ORDER'
           - TRIGGER: The core question explicitly asks for an Order document ("คำสั่ง").
           - EXCEPTION: If the query just uses verbs like "สั่งการ" (to command) or "ผู้ว่าการสั่ง" (Governor orders), route to GENERAL.

        3. 'GUIDELINE'
           - TRIGGER: The core question asks for the existence, content, or details of a Guideline document (e.g., "ขอแนวทาง...", "มีแนวทาง...หรือไม่", "ตามแนวทาง").
           - CRITICAL EXCEPTION: If "แนวทาง" is ONLY used as a descriptive noun in the Topic (e.g., "แนวทางการตรวจสอบ") AND the core question is a broad "how-to" (e.g., "ให้ดำเนินการอย่างไร"), route to GENERAL.
           - RULE OF THUMB: 
             - "มีแนวทางสำหรับการประเมินความเสี่ยงหรือไม่" -> GUIDELINE (Core question asks if a guideline exists).
             - "แนวทางการตรวจสอบ... ให้ดำเนินการอย่างไร" -> GENERAL (Core question asks how to proceed).
             - "การกำหนดประเด็น... และแนวทางการตรวจสอบ... มีแนวทางการดำเนินการเพิ่มเติมหรือไม่" -> GUIDELINE (The core question at the end explicitly asks "มีแนวทาง...หรือไม่").

        4. 'REGULATION'
           - TRIGGER: The core question explicitly asks for a Regulation document ("ตามระเบียบ...", "ระเบียบว่าด้วย...").

        5. 'GENERAL'
           - TRIGGER: Broad "how-to" questions (e.g., "ให้ดำเนินการอย่างไร", "ต้องทำอย่างไร").
           - FALLBACK: If the keywords are used as general vocabulary rather than requesting a specific document title, or if no keywords match, route to GENERAL.

        ### OUTPUT INSTRUCTION:
        Output ONLY the category name: REGULATION, ORDER, GUIDELINE, STANDARD, or GENERAL. Do not add any other text.
        """),
        ("human", "History: {history}\n\nQuery: {query}")
    ])  

    chain = routing_prompt | llm | StrOutputParser()
    
    try:
        decision = await chain.ainvoke({"history": history_str, "query": query})
        decision = decision.strip().upper()

        if "STANDARD" in decision: return "STANDARD"
        if "ORDER" in decision: return "ORDER"
        if "GUIDELINE" in decision: return "GUIDELINE"
        if "REGULATION" in decision: return "REGULATION"
        
        return "GENERAL"
        
    except Exception as e:
        print(f"Routing Error: {e}")
        return "GENERAL"
    
async def handle_legal_rag(query: str, history: list, llm:Any, retriever:Retriever):
    route = await get_legal_route(query, history, llm)
    if route == "ORDER":
        retrieved_docs = await retriever.retrieve_order(user_query=query, k=3, history=history)
        
    elif route == "GUIDELINE":
        retrieved_docs = await retriever.retrieve_guideline(user_query=query, k=3, history=history)
        
    elif route == "STANDARD":
        retrieved_docs = await retriever.retrieve_standard(user_query=query, k=3, history=history)
    elif route == "REGULATION" :
        retrieved_docs = await retriever.retrieve_regulation(user_query=query, k=3, history=history)
    else:
        retrieved_docs = await retriever.retrieve_general(query=query, k=3, history=history)

    context_str = format_regulation_context(retrieved_docs)
    history_str = "\n".join([f"{msg.type}: {msg.content}" for msg in history[-5:]]) if history else "No history."
    parser = JsonOutputParser(pydantic_object=LegalResponseSchema)
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", """
        ### ROLE
        You are a specialized Thai Legal Assistant for the State Audit Office (สตง.).
        Provide a helpful, direct answer followed by structured legal references in JSON format.

        ### CRITICAL FORMATTING RULES
        1. NO MARKDOWN: Do not use double asterisks (**), italics, or bolding in the 'answer_text'. Use plain text only.
        2. NO HALLUCINATED SECTIONS: When the context says "ให้นำหลักเกณฑ์ตาม (๑) มาใช้บังคับ" within a specific Section (e.g., Section 26), identify it correctly as "ข้อ 26 (1)". Do not guess the Section number if it is not explicitly linked in that sentence.

        ### INSTRUCTIONS FOR 'answer_text'
        1. Direct Answer First: Summarize the core meaning in 1-2 sentences.
        2. Mandatory In-text Citations: Every legal point must be followed by (จาก [ชื่อเอกสาร]).
        3. Structure: 
           - For Regulations: "ตามข้อ [เลขข้อ] ของ [ชื่อระเบียบ] กำหนดว่า..."
           - For Guidelines: "นอกจากนี้ ตาม [ชื่อแนวทาง] กำหนดว่า..."
        4. Precise Referencing: If a sub-clause points to another sub-clause (e.g., "ตาม (1)"), ensure you refer to it as the full clause name (e.g., "ข้อ 26 (1)").

        ### INSTRUCTIONS FOR 'used_law_names'
        - List ONLY titles cited in the 'answer_text'. Accuracy is mandatory.

        {format_instructions}

        ### DATA SOURCES:
        - Context: {context}
        - History: {history}
        """),
        ("human", "User Query: {query}")
    ])
    
    chain = (
        {
            "context": lambda x: context_str,
            "history": lambda x: history_str, 
            "query": lambda x: query,
            "format_instructions": lambda x: parser.get_format_instructions()
        }
        | prompt 
        | llm
        | parser
    )
    try:
        result = await chain.ainvoke({})
        
        answer = result.get("answer_text", "ขออภัย ไม่พบข้อมูลที่เกี่ยวข้อง")
        refs = result.get("used_law_names", [])
        
        return answer, refs

    except Exception as e:
        print(f"Extraction Error: {e}")
        return "ขออภัย ระบบขัดข้องในการประมวลผลข้อมูลทางกฎหมาย", []  
