import json
from datetime import datetime
from typing import List, Dict, Any
from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from src.app.llm.typhoon import TyphoonLLM
from src.db.vector_store import get_vectorstore

class Retriever:
    def __init__(self):
        self.vectorstore = get_vectorstore() 
        self.llm = TyphoonLLM().get_model()
        
        # DEFINED KNOWN FILES (Update this list if you add more files)
        self.VALID_FILES = [
            "regulation_v2566.txt",
            "regulation_v2568.txt"
        ]

    async def _extract_query_intent(self, query: str, history_messages: list) -> Dict[str, Any]:
        """
        Uses LLM to parse intent, restricting filenames to known valid ones.
        """
        valid_files_str = ", ".join(self.VALID_FILES)
        
        system_prompt = f"""
        You are a search query optimizer for legal regulations.
        
        KNOWN FILES IN DATABASE: [{valid_files_str}]
        
        Analyze the user's input (Thai or English) and extract:
        1. 'date': A specific date mentioned (YYYY-MM-DD). If none, return null.
        2. 'file': The specific filename implied. 
           - RULE: Only return a filename if the user EXPLICITLY mentions a year/version (e.g. "Year 2566" -> "regulation_v2566.txt"). 
           - If the user just says "Regulation" or "OAG Regulation" without a year, return null.
           - MUST be one of the KNOWN FILES.
        3. 'search_query': The cleaned core question (e.g. "ข้อ 9", "เบี้ยเลี้ยง"). Remove date/file references.
        4. 'is_exact_clause': boolean, true if user asks for specific clause number (e.g. "ข้อ 9", "หมวด 2").
        
        Return JSON only.
        """
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", "{input}")
        ])
        
        chain = prompt | self.llm | StrOutputParser()
        
        try:
            result = await chain.ainvoke({"input": query})
            clean_json = result.replace("```json", "").replace("```", "").strip()
            return json.loads(clean_json)
        except Exception as e:
            print(f"⚠️ Intent Extraction Failed: {e}. Fallback to raw query.")
            return {
                "date": None, 
                "file": None, 
                "search_query": query, 
                "is_exact_clause": False
            }

    async def retrieve(self, user_query: str, k: int = 4) -> List[Document]:
        # 1. Understand Intent
        intent = await self._extract_query_intent(user_query)
        
        query_text = intent.get("search_query") or user_query
        target_file = intent.get("file")
        query_date = intent.get("date")
        is_exact = intent.get("is_exact_clause", False)

        # 2. Define Search Config
        # Use Alpha=0.5 (Balanced) or 0.7 (Vector-heavy) for Thai 
        # (Standard BM25 keyword search struggles with Thai tokenization "ข้อ 9")
        alpha_val = 0.5 
        
        # 3. Construct Filters
        conditions = []
        
        # If user DID NOT specify a date, we usually default to "Today".
        # But we will save this logic for the "Strict" search first.
        if query_date:
            target_date_iso = f"{query_date}T00:00:00Z"
        else:
            target_date_iso = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

        # Base time filter (Active Laws)
        time_filter = {
            "operator": "And",
            "operands": [
                {"path": ["valid_from"], "operator": "LessThanEqual", "valueString": target_date_iso},
                {"path": ["valid_until"], "operator": "GreaterThanEqual", "valueString": target_date_iso}
            ]
        }
        
        # File filter
        file_filter = None
        if target_file and target_file in self.VALID_FILES:
            file_filter = {"path": ["source"], "operator": "Equal", "valueString": target_file}

        # Combine filters for the PRIMARY search
        primary_conditions = [time_filter]
        if file_filter:
            primary_conditions.append(file_filter)
            
        final_filter = {"operator": "And", "operands": primary_conditions}

        # 4. EXECUTE PRIMARY SEARCH (Strict Time)
        print(f"🕵️ Attempt 1: Searching Active Laws ({target_date_iso})...")
        try:
            docs = self.vectorstore.similarity_search(
                query_text, k=k,
                search_kwargs={"filters": final_filter, "hybrid_search": True, "alpha": alpha_val}
            )
        except Exception as e:
            print(f"⚠️ Search Error: {e}")
            docs = []

        # 5. FALLBACK SEARCH (If 0 results found)
        # If we found nothing AND the user didn't specify a date/file manually, 
        # they might be looking for an old law without knowing it.
        if not docs and not query_date:
            print(f"⚠️ No active laws found. Falling back to ALL TIME search...")
            
            # Remove Time Filter, Keep File Filter (if any)
            fallback_filter = file_filter if file_filter else None
            
            try:
                docs = self.vectorstore.similarity_search(
                    query_text, k=k,
                    search_kwargs={"filters": fallback_filter, "hybrid_search": True, "alpha": alpha_val} if fallback_filter else {"hybrid_search": True, "alpha": alpha_val}
                )
                
                # Tag these docs so the Chatbot knows they might be expired
                for d in docs:
                    d.metadata["_fallback_used"] = True
                    d.metadata["_analysis_date"] = "ALL TIME (Including Expired)"
                    
            except Exception as e:
                print(f"⚠️ Fallback Error: {e}")
                docs = []
        else:
            # Mark normal docs
            for d in docs:
                d.metadata["_analysis_date"] = target_date_iso

        return docs