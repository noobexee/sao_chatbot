import asyncio
from typing import List, Optional, Dict, Any
from datetime import datetime

from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from sentence_transformers import CrossEncoder
from langchain_core.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field 
from weaviate.classes.query import Filter 
from src.app.llm.typhoon import TyphoonLLM
from src.db.vector_store import get_vectorstore
from dotenv import load_dotenv



class SearchIntent(BaseModel):
    """Structure for the optimized legal search query."""
    
    rewritten_query: str = Field(
        description="The query rewritten into formal legal terminology. Combine all intent into one clear sentence. (e.g., Change 'how to submit letter' to 'Criteria for receiving written complaints')"
    )
    law_name: Optional[str] = Field(
        description="Specific law or regulation name if explicitly mentioned. (e.g., 'ระเบียบสำนักงานตรวจเงินแผ่นดิน'). Return None if not mentioned.",
        default=None
    )
    doc_type: Optional[str] = Field(
        description="The type of document explicitly requested (e.g., 'ระเบียบ', 'คำสั่ง', 'พรบ', 'ประกาศ'). Return None if generic.",
        default=None
    )
    search_date: str = Field(
        description="The reference date for the search context in YYYY-MM-DD format."
    )

class Retriever:
    def __init__(self):
        self.vectorstore = get_vectorstore() 
        self.llm = TyphoonLLM().get_model()
        self.reranker = CrossEncoder('BAAI/bge-reranker-v2-m3', device='cpu')
        self.parser = PydanticOutputParser(pydantic_object=SearchIntent)

    async def generate_search_queries(self, user_query: str, history: List = None) -> Dict[str, Any]:

        if history is None:
            history = []

        current_date = datetime.now().strftime("%Y-%m-%d")


        system_prompt = """คุณเป็นผู้เชี่ยวชาญด้านการสืบค้นกฎหมายและระเบียบราชการ (Legal Search Specialist)
        หน้าที่ของคุณคือ "แปลง" คำถามของผู้ใช้ (User Query) ให้เป็น "คำค้นหาทางกฎหมาย" (Legal Search Query) ที่แม่นยำที่สุด
        
        บริบทเวลาปัจจุบัน: {current_date}

        ### คำสั่ง (Instructions):
        1. **ห้ามแยกข้อย่อย:** รวมความต้องการทั้งหมดเป็น "ประโยคค้นหาเดียว"
        
        2. **แปลงภาษาพูดเป็นภาษาทางการ:**
           - ตัดคำฟุ่มเฟือย และใช้ศัพท์ราชการ (เช่น "เบิกเงิน" -> "ระเบียบการเบิกจ่าย")

        3. **การจัดการวันที่ (Date Handling):**
           - หากระบุวันที่เป็น พ.ศ. ให้แปลงเป็น ค.ศ. (ลบ 543) สำหรับฟิลด์ search_date
           - ตัวอย่าง: "21 ม.ค. 2567" -> "2024-01-21"

        4. **การแปลงเลขเป็นเลขไทย (Thai Numerals) [สำคัญมาก]:**
           - ในส่วนของ `rewritten_query` หากมีการระบุตัวเลขเจาะจง เช่น มาตรา, ข้อ, หรือ จำนวนเงิน ต้องแปลงเลขอารบิก (0-9) เป็นเลขไทย (๐-๙) เสมอ
           - ตัวอย่าง: "ข้อ 39" -> "ข้อ ๓๙"
           - ตัวอย่าง: "มาตรา 112" -> "มาตรา ๑๑๒"
           - ตัวอย่าง: "ฉบับที่ 2" -> "ฉบับที่ ๒"

        5. **Extraction:** ระบุชื่อกฎหมายและประเภทเอกสารหากมี

        {format_instructions}
        """
        
        # ... rest of your code ...
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", "ประวัติการสนทนา:\n{history}\n\nคำถาม: {input}")
        ])

        chain = prompt | self.llm | self.parser

        try:
            # Execute the chain
            response = await chain.ainvoke({
                "input": user_query, 
                "history": history,
                "format_instructions": self.parser.get_format_instructions(),
                "current_date": current_date
            })
            
            return response.dict()

        except Exception as e:
            print(f"⚠️ Query Parsing Failed: {e}")
            return {
                "rewritten_query": user_query,
                "law_name": None,
                "doc_type": None,
                "search_date": current_date
            }
    def _build_filters(self, search_date: str, law_name: str = None, doc_type: str = None):
        filters = []
        if "T" not in search_date:
            rfc3339_date = f"{search_date}T00:00:00Z"
        else:
            rfc3339_date = search_date
            
        date_filter = (
            Filter.by_property("valid_from").less_or_equal(rfc3339_date) & 
            Filter.by_property("valid_until").greater_or_equal(rfc3339_date)
        )
        filters.append(date_filter)

        if law_name:
            filters.append(Filter.by_property("law_name").like(f"*{law_name}*"))

        if doc_type:
             filters.append(Filter.by_property("doc_type").like(f"*{doc_type}*"))

        composite_filter = filters[0]
        for f in filters[1:]:
            composite_filter = composite_filter & f
            
        return composite_filter

    def _rerank_documents(self, user_query: str, docs: List[Document], top_k: int = 3) -> List[Document]:
        if not docs: return []
        pairs = [[user_query, doc.page_content] for doc in docs]
        scores = self.reranker.predict(pairs)
        doc_score_pairs = list(zip(docs, scores))
        doc_score_pairs.sort(key=lambda x: x[1], reverse=True)
        return [doc for doc, score in doc_score_pairs[:top_k]]

    async def retrieve(self, user_query: str, history: List = None, k: int = 5, search_date: str = None) -> List[Document]:
        
        analysis_result = await self.generate_search_queries(user_query, history)
        
        search_queries = [analysis_result.get("rewritten_query", "")]
        extracted_date = analysis_result.get("search_date")
        law_name_filter = analysis_result.get("law_name")
        doc_type_filter = analysis_result.get("doc_type")

        final_date = search_date if search_date else (extracted_date)
        print(f"search date: {final_date}")

        try:
            time_filter = self._build_filters(
                search_date=final_date,
                law_name=law_name_filter,
                doc_type=doc_type_filter
            )
            if law_name_filter or doc_type_filter:
                print(f"Sniper Filter Active: Law='{law_name_filter}', Type='{doc_type_filter}'")
        except ValueError as e:
            print(f"Filter Error: {e}")
            time_filter = None

        all_docs = []
        
        print(f"Searching: {search_queries} @ {final_date}")
        for query in search_queries:
            docs = self.vectorstore.similarity_search(
                query, 
                k=k, 
                alpha=0.5,
                filters=time_filter
            )
            all_docs.extend(docs)

        unique_docs_map = {doc.page_content: doc for doc in all_docs}
        unique_candidates = list(unique_docs_map.values())
        
        print(f"Found {len(unique_candidates)} candidates. Re-ranking...")
        final_docs = self._rerank_documents(user_query, unique_candidates, top_k=5)

        return final_docs


async def main():
    query = "เรื่องที่มาจากการ้องเรียนมีที่มาจากอะไรบ้าง"
    
    load_dotenv()
    retriever = Retriever()
    
    try:
        retrieved_docs = await retriever.retrieve(query) 
        if retrieved_docs:
            print(f"\n✅ Found {len(retrieved_docs)} results:\n")
            for i, doc in enumerate(retrieved_docs, 1):
                source = doc.metadata.get("source", "Unknown File")
                law_name = doc.metadata.get("law_name", "N/A")
                valid_from = doc.metadata.get("valid_from", "N/A")
                valid_until = doc.metadata.get("valid_until", "N/A")
                doc_type = doc.metadata.get("doc_type", "N/A")
                
                print(f"{i} Law name: {law_name}")
                print(f"{i} valid_from: {valid_from}")
                print(f"{i} valid_until: {valid_until}")
                print(f"{i} doc_type: {doc_type}")
                print(f"Content: {doc.page_content}") 
                print("-" * 60)
        else:
            print("No documents found.")
            
    finally:
        print("\nClosing connection...")
        if hasattr(retriever.vectorstore, "client"):
            retriever.vectorstore.client.close()
        elif hasattr(retriever.vectorstore, "_client"):
            retriever.vectorstore._client.close()

async def main2():
    query = "การกำหนดประเด็นการตรวจสอบ เกณฑ์ที่ใช้ในการตรวจสอบ และแนวทางการตรวจสอบ รวมถึงระยะเวลาในการดำเนินการ กรณีเรื่องที่คัดเลือกมาจากการประเมินความเสี่ยงของหน่วยรับตรวจ ให้ดำเนินการอย่างไร"
    test_date = "2025-12-20"
    
    retriever = Retriever()
    
    print(f"--- Testing retrieverwith date: {test_date} ---")
    
    try:
        retrieved_docs = await retriever.generate_search_queries(query)
        print(retrieved_docs)
        
            
    finally:
        print("\nClosing connection...")
        if hasattr(retriever.vectorstore, "client"):
            retriever.vectorstore.client.close()
        elif hasattr(retriever.vectorstore, "_client"):
            retriever.vectorstore._client.close()

if __name__ == "__main__":
    asyncio.run(main())