from typing import List, Optional, Dict, Any
from datetime import datetime

from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field 
from src.app.chatbot.utils.embedding import BGEEmbedder
from src.app.llm.typhoon import TyphoonLLM
from src.db.vector_store import load_faiss_index
from ..utils import time_execution


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
        self.embedder = BGEEmbedder(model_name="BAAI/bge-m3")
        self.llm = TyphoonLLM().get_model()
        self.parser = PydanticOutputParser(pydantic_object=SearchIntent)
        
    @time_execution
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
            print(f" Query Parsing Failed: {e}")
            return {
                "rewritten_query": user_query,
                "law_name": None,
                "doc_type": None,
                "search_date": current_date
            }

    def filter_search(self, candidates, k, search_date=None):
        if not search_date:
            target_dt = datetime.now()
        else:
            try:
                target_dt = datetime.strptime(search_date, "%Y-%m-%d")
            except ValueError:
                target_dt = datetime.now()

        filtered_results = []
        print(target_dt)

        for match in candidates:
            eff_str = match.get("effective_date") or "1900-01-01"
            exp_str = match.get("expire_date") or "9999-12-31"
            
            try:
                eff_dt = datetime.strptime(eff_str, "%Y-%m-%d")
                exp_dt = datetime.strptime(exp_str, "%Y-%m-%d")
            except ValueError:
                continue

            if eff_dt <= target_dt <= exp_dt:
                filtered_results.append(match)
            
            if len(filtered_results) >= k:
                break
                
        return filtered_results

    def similarity_search(self, query_text, embedder, k=5, search_date=None):
        index, metadata_list = load_faiss_index("storage/faiss_index")
        query_vector = embedder.embed_query(query_text)

        distances, indices = index.search(query_vector, k * 10)
        
        candidates = []
        for i, idx in enumerate(indices[0]):
            if idx == -1: continue
            
            match = metadata_list[idx]
            candidates.append({
                "score": float(distances[0][i]),
                "law_name": match.get("law_name"),
                "section": match.get("id"),
                "text": match.get("text"),
                "version": match.get("version"),
                "effective_date": match.get("effective_date"),
                "expire_date": match.get("expire_date")
            })

        answer = self.filter_search(candidates, k, search_date)

        return answer

    async def retrieve(self, user_query: str, history: List = None, k: int = 10, search_date: str = None) -> List[Document] :

        search_result = self.similarity_search(
            user_query, 
            self.embedder,
            5, 
        )
        
        return search_result
        
        
        
