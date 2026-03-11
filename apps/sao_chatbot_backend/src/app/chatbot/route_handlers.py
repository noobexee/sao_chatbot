import asyncio
from typing import List, Any, Dict, Optional
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser
from pydantic import BaseModel, Field
from langchain_core.output_parsers import JsonOutputParser
from src.db.repositories.document_repository import DocumentRepository
from src.app.chatbot.schemas import RAGResponse
from src.app.chatbot.retriever import Retriever
from .utils.formatters import format_regulation_context
from thefuzz import process, fuzz

class LegalResponseSchema(BaseModel):
    answer_text: str = Field(description="The natural Thai response starting with 'จากข้อ... ของระเบียบ...'")
    used_law_names: List[str] = Field(description="List of exact law_names or guideline_names from the context that were used to answer the question.")

class FileResponse(BaseModel):
    answer_text: str = Field(description="A polite, formal Thai response (e.g., 'ขออนุญาตนำส่งเอกสาร').")
    target_files: List[str] = Field(description="List of exact filenames found. Empty list if none.")

async def handle_chitchat(query: str, history: list, llm) -> RAGResponse:

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
    
    return RAGResponse(answer=answer, ref=[])

async def handle_file_request(query: str, history: list, llm: Any) -> RAGResponse:
    parser = JsonOutputParser(pydantic_object=FileResponse)
    
    repo = DocumentRepository()
    try:
        all_docs = await asyncio.to_thread(repo.list_documents)
    except Exception as e:
        print(f"Database error: {e}")
        return RAGResponse(answer="ขออภัยครับ ไม่สามารถเชื่อมต่อฐานข้อมูลได้ในขณะนี้", ref={})

    title_to_id = {doc["title"]: doc["id"] for doc in all_docs if doc.get("title") and doc.get("id")}
    available_titles = list(title_to_id.keys())

    if not available_titles:
        return RAGResponse(answer="ระบบยังไม่มีไฟล์เอกสารในขณะนี้ครับ", ref={})

    fuzzy_results = process.extract(
        query, 
        available_titles, 
        limit=10, 
        scorer=fuzz.token_set_ratio
    )
    
    matched_titles = [res[0] for res in fuzzy_results if res[1] >= 65]

    if matched_titles:
        files_context = "Found the following exact files in the database:\n" + "\n".join(matched_titles)
        system_instruction = "Inform the user that you found the requested file(s) and return the exact file names in the 'target_files' list."
    else:
        files_context = "System checked but NO files matched the user's query."
        system_instruction = "Politely apologize to the user and state that the requested file could not be found. Return an empty list for 'target_files'."

    prompt = ChatPromptTemplate.from_messages([
        ("system", """
        You are a professional File Librarian for the State Audit Office (SAO / สตง.).
        Your task is to review the 'System Search Results' and provide the correct file(s) to the user.

        RULES:
        1. Tone: Respond in polite, formal Thai suitable for a government agency.
        2. Multiple Files: You can return MORE THAN ONE file in the 'target_files' list.
        3. Version Handling (พ.ศ. / ฉบับที่): 
           - If the user asks for a document WITHOUT specifying a year or version, you MUST return ALL versions of that document found in the 'System Search Results'.
           - If the user asks for a SPECIFIC year or version, return ONLY the file that matches that specific year.
        4. Strict Formatting: You MUST copy the file names EXACTLY as they appear in the 'System Search Results' into the 'target_files' list. Do not change spelling, spacing, or extensions.
        5. No Hallucinations: Do not invent file names. If 'System Search Results' says NO files matched, 'target_files' MUST be an empty list [].
        
        {format_instructions}
        
        System Instruction: {instruction}
        """),
        ("human", """
        System Search Results:
        {context}

        Chat History: {history}
        User Query: {query}
        """)
    ])
    
    chain = (
        {
            "context": lambda x: files_context,
            "instruction": lambda x: system_instruction,
            "query": lambda x: query,
            "history": lambda x: history,
            "format_instructions": lambda x: parser.get_format_instructions()
        }
        | prompt 
        | llm
        | parser
    )

    try:
        llm_response = await chain.ainvoke({})
        
        ref_dict = {}
        for title in llm_response.get("target_files", []):
            if title in title_to_id:
                ref_dict[title] = title_to_id[title] 
                
        return RAGResponse(
            answer=llm_response.get("answer_text", ""),
            ref=ref_dict
        )
            
    except Exception as e:
        print(f"Error parsing JSON: {e}")
        return RAGResponse(answer="ขออภัยครับ เกิดข้อผิดพลาดในการค้นหาไฟล์ของระบบ", ref={})
    
 
  
async def handle_FAQ(query: str, history: list, llm:Any) -> RAGResponse:

    return RAGResponse(answer="ขออภัยครับ ผมไม่มีข้อมูลในส่วนนี้ (ข้อมูลติดต่อหรือที่อยู่หน่วยงาน) ผมสามารถให้ข้อมูลได้เฉพาะเรื่องกฎหมายและระเบียบการตรวจสอบเท่านั้นครับ", ref=[])

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

def map_references_to_document_ids(retrieved_docs: List[Dict[str, Any]], refs_list: List[str]) -> Dict[str, Optional[str]]:
    """
    Maps LLM-generated reference strings to their corresponding document IDs 
    based on the retrieved documents metadata.
    """
    doc_mapping = {}
    for doc in retrieved_docs:
        if "law_name" in doc and "document_id" in doc:
            doc_mapping[doc["law_name"]] = doc["document_id"]
            
        for related_doc in doc.get("related_documents", []):
            if "law_name" in related_doc and "document_id" in related_doc:
                doc_mapping[related_doc["law_name"]] = related_doc["document_id"]

    ref_dict = {}
    for ref in refs_list:
        ref_dict[ref] = None 
        for db_law_name, db_doc_id in doc_mapping.items():
            if db_law_name in ref or ref in db_law_name:
                ref_dict[ref] = db_doc_id
                break 
                
    return ref_dict

async def handle_legal_rag(query: str, history: list, llm:Any, retriever:Retriever, k=3) -> RAGResponse:
    route = await get_legal_route(query, history, llm)
    if route == "ORDER":
        retrieved_docs = await retriever.retrieve_order(user_query=query, k=k, history=history)
    elif route == "GUIDELINE":
        retrieved_docs = await retriever.retrieve_guideline(user_query=query, k=k, history=history)
    elif route == "STANDARD":
        retrieved_docs = await retriever.retrieve_standard(user_query=query, k=k, history=history)
    elif route == "REGULATION" :
        retrieved_docs = await retriever.retrieve_regulation(user_query=query, k=k, history=history)
    else:
        retrieved_docs = await retriever.retrieve_general(query=query, k=k, history=history)

    context_str = format_regulation_context(retrieved_docs)
    history_str = "\n".join([f"{msg.type}: {msg.content}" for msg in history[-k:]]) if history else "No history."
    parser = JsonOutputParser(pydantic_object=LegalResponseSchema)
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", """
        ### ROLE
        You are a specialized Thai Legal Assistant for the State Audit Office (สตง.).
         
        ### MANDATORY JSON FORMATTING
        - YOUR ENTIRE RESPONSE MUST BE A VALID JSON OBJECT. 
        - DO NOT provide any text, greetings, or summaries outside of the JSON keys.
        - Start with '{{' and end with '}}'.
         
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
        1. List the legal citations used in 'answer_text' exactly as they appear in the REFERENCE_LABEL.
        2. STRICT FORMATTING RULES:
        - If the document is a 'ระเบียบ': Use "ข้อ [เลขข้อ] [ชื่อระเบียบ]" (e.g., ข้อ 5 ระเบียบสำนักงานตรวจเงินแผ่นดิน).
        - For all other types (คำสั่ง, แนวทาง, มาตรฐาน): Use ONLY the law name (e.g., คำสั่งสำนักงานตรวจเงินแผ่นดิน ที่ 1/2566).
        3. Do not add any text or bolding inside the JSON array.

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
        refs_list = result.get("used_law_names", [])
        ref_dict = map_references_to_document_ids(retrieved_docs, refs_list)
        
        return RAGResponse(answer=answer, ref=ref_dict)

    except Exception as e:
        print(f"Extraction Error: {e}")
        return "ขออภัย ระบบขัดข้องในการประมวลผลข้อมูลทางกฎหมาย", {}
