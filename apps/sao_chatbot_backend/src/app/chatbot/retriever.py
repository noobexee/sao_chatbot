import re
import os 
import json
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime
from pythainlp import word_tokenize
import numpy as np
from rank_bm25 import BM25Okapi
from src.app.utils.embedding import BGEEmbedder
from src.db.vector_store.vector_store import load_faiss_index 
from src.app.llm.typhoon import TyphoonLLM
from .utils.formatters import thai_to_arabic, normalize_regulation_id

REGULATION_PATH = "storage/regulations"
OTHERS_PATH = "storage/others"

class Retriever:
    def __init__(self):
        self.embedder = BGEEmbedder(model_name="BAAI/bge-m3")
        self.llm = TyphoonLLM().get_model()
        
        self.reg_index = None
        self.reg_metadata = []
        self.reg_bm25 = None

        self.other_index = None
        self.other_metadata = []
        self.other_bm25 = None

        self.master_map = self._load_master_map("storage/master_map.json")
        self.reload_resources()

    def reload_resources(self):
        print("Reloading retriever resources...") 
        self.reg_index, self.reg_metadata, self.reg_bm25 = self._load_store(REGULATION_PATH)
        self.other_index, self.other_metadata, self.other_bm25 = self._load_store(OTHERS_PATH)
    
    def _load_master_map(self, path: str) -> Dict:
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    
    def super_normalize(self, text: str) -> str:
        """Converts to Arabic AND removes all whitespace for a 'pure' string match."""
        if not text: return ""
        # 1. Convert numerals to Arabic
        text = thai_to_arabic(text)
        # 2. Remove ALL whitespace, newlines, and non-breaking spaces
        text = re.sub(r'[\s\u00A0\t\n\r]+', '', text)
        return text
    
    def _load_store(self, path: str) -> Tuple[Any, List, Any]:
        """
        Internal Helper: Loads Index, Metadata, and builds BM25 for a given path.
        """
        try:
            index, metadata = load_faiss_index(path)
        except Exception as e:
            print(f"Warning: Could not load index at {path}: {e}")
            return None, [], None

        if not metadata:
            return None, [], None

        # Include 'law_name' in the BM25 corpus so titles become searchable
        corpus = [ 
            word_tokenize(doc.get("text", "").lower(), engine="newmm") 
            for doc in metadata
        ]
        bm25 = BM25Okapi(corpus) if corpus else None
        
        return index, metadata, bm25

    def _boost_by_title(self, candidates: List[Dict], keywords: List[str]) -> List[Dict]:
        """
        Artificially boosts the score of candidates if the user's keywords 
        appear in the document's title (law_name).
        """
        for cand in candidates:
            law_name = cand.get("law_name", "").lower()
            if not law_name: 
                continue
            
            overlap = sum(1 for kw in keywords if kw.lower() in law_name)
            
            if overlap > 0:
                current_score = cand.get("hybrid_score", 0)
                cand["hybrid_score"] = current_score + (overlap * 0.05)
            
        return sorted(candidates, key=lambda x: x.get("hybrid_score", 0), reverse=True)
    
    async def extract_keywords(self, query_text: str) -> List[str]:
        """Uses LLM to extract keywords for BM25."""
        prompt = f"""
        Extract legal entities and technical terms from this Thai query.
        Return only comma-separated keywords.
        Query: "{query_text}"
        Keywords:"""
        try:
            response = await self.llm.ainvoke(prompt)
            raw_text = response.content.strip() if hasattr(response, 'content') else str(response)
            keywords = [k.strip() for k in raw_text.split(",") if k.strip()]
            
            # Fallback if no commas found
            if len(keywords) <= 1:
                keywords = [k.strip() for k in raw_text.split() if k.strip()]
            return keywords
        except Exception as e:
            print(f"Keyword extraction failed: {e}")
            return [query_text]

    def _filter_date(self, candidates, k, search_date=None):
        if not search_date:
            target_dt = datetime.now()
        else:
            try:
                target_dt = datetime.strptime(search_date, "%Y-%m-%d")
            except ValueError:
                target_dt = datetime.now()

        filtered_results = []
        seen_ids = set()

        for match in candidates:
            law_name = match.get("law_name", "")
            chunk_id = match.get("id") or match.get("document_id", "")
            unique_key = f"{law_name}|{chunk_id}"
            
            if unique_key in seen_ids: 
                continue

            eff_raw = match.get("effective_date")
            exp_raw = match.get("expire_date")

            if not eff_raw or str(eff_raw).strip().lower() == "null":
                eff_str = "1900-01-01"
            else:
                eff_str = str(eff_raw).strip()

            if not exp_raw or str(exp_raw).strip().lower() == "null":
                exp_str = "9999-12-31"
            else:
                exp_str = str(exp_raw).strip()
            
            try:
                eff_dt = datetime.strptime(eff_str, "%Y-%m-%d")
                exp_dt = datetime.strptime(exp_str, "%Y-%m-%d")
            except ValueError:
                eff_dt = datetime.strptime("1900-01-01", "%Y-%m-%d")
                exp_dt = datetime.strptime("9999-12-31", "%Y-%m-%d")

            if eff_dt <= target_dt <= exp_dt:
                filtered_results.append(match)
                seen_ids.add(unique_key)
            
            if len(filtered_results) >= k:
                break
                
        return filtered_results

    def _run_rrf_fusion(self, vector_results, keyword_results, metadata_list, k, v_weight=0.5):
        """Combines results using Reciprocal Rank Fusion."""
        rrf_scores = {}
        c = 60
        
        for item in vector_results:
            idx, rank = item['idx'], item['rank']
            rrf_scores[idx] = rrf_scores.get(idx, 0) + (v_weight * (1.0 / (rank + c)))

        for item in keyword_results:
            idx, rank = item['idx'], item['rank']
            rrf_scores[idx] = rrf_scores.get(idx, 0) + ((1 - v_weight) * (1.0 / (rank + c)))

        sorted_indices = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)
        
        matches = []
        for idx, score in sorted_indices:
            if idx < len(metadata_list):
                doc = metadata_list[idx].copy()
                doc["hybrid_score"] = score
                matches.append(doc)
        return matches

    def vector_search_regulation(self, query_text: str, k: int) -> List[Dict]:
        if not self.reg_index: return []
        vec = self.embedder.embed_query(query_text)
        query_array = np.atleast_2d(vec).astype('float32')
        D, I = self.reg_index.search(query_array, k * 5)
        return [{"idx": int(idx), "rank": i} for i, idx in enumerate(I[0]) if idx != -1]

    def keyword_search_regulation(self, keyword_list: List[str], k: int) -> List[Dict]:
        if not self.reg_bm25 or not keyword_list: return []
        tokens = []
        for p in keyword_list: tokens.extend(word_tokenize(p.lower(), engine="newmm"))
        scores = self.reg_bm25.get_scores(tokens)
        top_idx = np.argsort(scores)[::-1][:k * 5]
        return [{"idx": int(i), "rank": r} for r, i in enumerate(top_idx) if scores[i] > 0]

    async def hybrid_search_regulation(self, query: str, k: int = 5, search_date: str = None):
        """Orchestrates hybrid search specifically for Regulations."""
        keywords = await self.extract_keywords(query)
        
        vec_res = self.vector_search_regulation(query, k)
        key_res = self.keyword_search_regulation(keywords, k)
        
        candidates = self._run_rrf_fusion(vec_res, key_res, self.reg_metadata, k)
        return self._filter_date(candidates, k, search_date)

    def vector_search_other(self, query_text: str, k: int) -> List[Dict]:
        if not self.other_index: return []
        vec = self.embedder.embed_query(query_text)
        query_array = np.atleast_2d(vec).astype('float32')
        D, I = self.other_index.search(query_array, k * 5)
        return [{"idx": int(idx), "rank": i} for i, idx in enumerate(I[0]) if idx != -1]

    def keyword_search_other(self, keyword_list: List[str], k: int) -> List[Dict]:
        if not self.other_bm25 or not keyword_list: return []
        tokens = []
        for p in keyword_list: tokens.extend(word_tokenize(p.lower(), engine="newmm"))
        scores = self.other_bm25.get_scores(tokens)
        top_idx = np.argsort(scores)[::-1][:k * 5]
        return [{"idx": int(i), "rank": r} for r, i in enumerate(top_idx) if scores[i] > 0]

    async def hybrid_search_other(self, query: str, k: int = 5, search_date: str = None):
        """Orchestrates hybrid search specifically for Guidelines/Orders."""
        keywords = await self.extract_keywords(query)
        
        vec_res = self.vector_search_other(query, k)
        key_res = self.keyword_search_other(keywords, k)
        
        candidates = self._run_rrf_fusion(vec_res, key_res, self.other_metadata, k)
        return self._filter_date(candidates, k, search_date)

    def get_related_document_titles(self, reg_doc: Dict) -> List[str]:
        if not self.master_map:
            return []

        # FIND THE LAW (Fuzzy Match)
        # We want "ระเบียบ...ตรวจสอบการปฏิบัติตามกฎหมาย" regardless of year/version
        full_law_name = reg_doc.get("law_name", "")
        core_law = re.sub(r'\(ฉบับที่.*?\)|พ\.ศ\..*$', '', full_law_name).strip()
        norm_core_law = self.super_normalize(core_law)

        law_mapping = {}
        for map_law_name, clauses in self.master_map.items():
            if norm_core_law in self.super_normalize(map_law_name) or self.super_normalize(map_law_name) in norm_core_law:
                law_mapping = clauses
                break
        
        if not law_mapping:
            return []

        # Extract base number from ID: "ข้อ ๒๖_p3" -> 26
        reg_id_digits = re.findall(r'[๐-๙0-9]+', normalize_regulation_id(reg_doc.get("id", "")))
        base_num = thai_to_arabic(reg_id_digits[0]) if reg_id_digits else ""
        
        # Extract sub-clause from text: "(๔)" -> 4
        text_content = reg_doc.get("text", "")
        sub_clause_match = re.search(r'^\s*\(([๐-๙0-9]+)\)', text_content)
        sub_num = thai_to_arabic(sub_clause_match.group(1)) if sub_clause_match else None

        all_titles = []
        for map_key, titles in law_mapping.items():
            map_key_arabic = thai_to_arabic(map_key)
            
            if sub_num:
                if base_num in map_key_arabic and f"({sub_num})" in map_key_arabic:
                    all_titles.extend(titles)
            
            else:
                if re.search(fr'\b{base_num}\b', map_key_arabic):
                    all_titles.extend(titles)

        return list(set(all_titles))
    
    async def retrieve(self, user_query: str, k: int = 3, history: list =[], search_date: str = None):
        reg_results = await self.hybrid_search_regulation(user_query, k, search_date)
        keywords = await self.extract_keywords(user_query)

        for reg in reg_results:
            allowed_titles = self.get_related_document_titles(reg)
            
            if not allowed_titles:
                reg["related_documents"] = []
                continue

            normalized_allowed = [self.super_normalize(t) for t in allowed_titles]

            vec_res = self.vector_search_other(user_query, k=20)
            key_res = self.keyword_search_other(keywords, k=20)
            candidates = self._run_rrf_fusion(vec_res, key_res, self.other_metadata, k=20)

            filtered_related = []
            seen_chunks = set()
            
            for cand in candidates:
                raw_cand_name = cand.get("law_name", "")
                norm_cand_name = self.super_normalize(raw_cand_name)
                
                is_match = False
                for norm_title in normalized_allowed:
                    if norm_title in norm_cand_name or norm_cand_name in norm_title:
                        is_match = True
                        break
                unique_key = f"{cand.get('law_name')}|{cand.get('id')}"
                if is_match and unique_key not in seen_chunks:
                    filtered_related.append(cand)
                    seen_chunks.add(cand.get("id"))
            
            active_related = self._filter_date(filtered_related, k=k, search_date=search_date)
            reg["related_documents"] = active_related

        return reg_results

    async def _retrieve_other_by_type(self, query: str, target_doc_type: str, k: int = 3, search_date: str = None):
        keywords = await self.extract_keywords(query)
        
        fetch_k = k * 5 
        vec_res = self.vector_search_other(query, fetch_k)
        key_res = self.keyword_search_other(keywords, fetch_k)
        
        # Run Fusion
        candidates = self._run_rrf_fusion(vec_res, key_res, self.other_metadata, fetch_k)
        
        # APPLY TITLE BOOSTING HERE
        boosted_candidates = self._boost_by_title(candidates, keywords)
        
        filtered_by_type = []
        seen_chunks = set()
        
        for cand in boosted_candidates:
            doc_type = cand.get("doc_type", "")
            
            if target_doc_type not in doc_type:
                continue
                
            unique_key = f"{cand.get('law_name')}|{cand.get('id')}"
            if unique_key not in seen_chunks:
                filtered_by_type.append(cand)
                seen_chunks.add(unique_key)
                
        return self._filter_date(filtered_by_type, k=k, search_date=search_date)

    async def retrieve_order(self, user_query: str, k: int = 3, history: list =[],search_date: str = None):
        """Retrieves ONLY Orders (คำสั่ง)"""
        return await self._retrieve_other_by_type(user_query, "คำสั่ง", k, search_date)

    async def retrieve_guideline(self, user_query: str, k: int = 3, history: list =[], search_date: str = None):
        """Retrieves ONLY Guidelines (แนวทาง)"""
        return await self._retrieve_other_by_type(user_query, "แนวทาง", k, search_date)

    async def retrieve_standard(self,user_query: str, k: int = 3, history: list =[], search_date: str = None):
        """Retrieves ONLY Standards (หลักเกณฑ์)"""
        return await self._retrieve_other_by_type(user_query, "หลักเกณฑ์", k, search_date)
    
    async def retrieve_regulation(self, user_query: str, k: int = 3, history: list =[], search_date: str = None):
        reg_results = await self.hybrid_search_regulation(user_query, k, search_date)
        keywords = await self.extract_keywords(user_query)

        for reg in reg_results:
            allowed_titles = self.get_related_document_titles(reg)
            
            if not allowed_titles:
                reg["related_documents"] = []
                continue

            normalized_allowed = [self.super_normalize(t) for t in allowed_titles]

            vec_res = self.vector_search_other(user_query, k=20)
            key_res = self.keyword_search_other(keywords, k=20)
            candidates = self._run_rrf_fusion(vec_res, key_res, self.other_metadata, k=20)

            filtered_related = []
            seen_chunks = set()
            
            for cand in candidates:
                raw_cand_name = cand.get("law_name", "")
                norm_cand_name = self.super_normalize(raw_cand_name)
                
                is_match = False
                for norm_title in normalized_allowed:
                    if norm_title in norm_cand_name or norm_cand_name in norm_title:
                        is_match = True
                        break
                unique_key = f"{cand.get('law_name')}|{cand.get('id')}"
                if is_match and unique_key not in seen_chunks:
                    filtered_related.append(cand)
                    seen_chunks.add(cand.get("id"))
            
            active_related = self._filter_date(filtered_related, k=k, search_date=search_date)
            reg["related_documents"] = active_related

        return reg_results

    async def retrieve_general(self, query: str, k: int = 3, search_date: str = None):
        """
        Searches across ALL databases (Regulations, Orders, Guidelines, Standards).
        Combines and ranks them with Legal Hierarchy Weighting.
        """
        # 1. Fetch from Regulations
        reg_candidates = await self.hybrid_search_regulation(query, k=k*2, search_date=search_date)
        
        # 2. Fetch from Others 
        other_candidates = await self.hybrid_search_other(query, k=k*2, search_date=search_date)
        
        # 3. Combine lists
        all_candidates = reg_candidates + other_candidates
        
        # ==========================================
        # NEW: LEGAL HIERARCHY BOOSTING
        # ==========================================
        for cand in all_candidates:
            law_name = cand.get("law_name", "")
            doc_type = cand.get("doc_type", "")
            score = cand.get("hybrid_score", 0)
            
            # Apply score multipliers based on legal hierarchy
            if "ระเบียบ" in doc_type or "ระเบียบ" in law_name:
                # Give Regulations a 30% boost so they dominate the top ranks
                cand["hybrid_score"] = score * 1.30  
                
            elif "คำสั่ง" in doc_type or "คำสั่ง" in law_name:
                # Give Orders a 10% boost
                cand["hybrid_score"] = score * 1.10  
                
            elif "หลักเกณฑ์" in doc_type or "หลักเกณฑ์" in law_name:
                # Give Standards a 5% boost
                cand["hybrid_score"] = score * 1.05  
                
            # Guidelines (แนวทาง) receive no boost (1.0x multiplier)
        # ==========================================

        # 4. Sort by the newly boosted hybrid scores
        all_candidates.sort(key=lambda x: x.get("hybrid_score", 0), reverse=True)
        
        # 5. Take the top k overall
        top_results = all_candidates[:k]
        
        # 6. Preserve Context (Fetch related guidelines for winning Regulations)
        for doc in top_results:
            law_name = doc.get("law_name", "")
            if "ระเบียบ" in law_name:
                allowed_titles = self.get_related_document_titles(doc)
                if allowed_titles:
                    normalized_allowed = [self.super_normalize(t) for t in allowed_titles]
                    keywords = await self.extract_keywords(query)
                    
                    vec_res = self.vector_search_other(query, k=15)
                    key_res = self.keyword_search_other(keywords, k=15)
                    other_cands = self._run_rrf_fusion(vec_res, key_res, self.other_metadata, k=15)
                    
                    filtered_related = []
                    seen_chunks = set()
                    
                    for cand in other_cands:
                        norm_cand_name = self.super_normalize(cand.get("law_name", ""))
                        is_match = any(nt in norm_cand_name or norm_cand_name in nt for nt in normalized_allowed)
                        
                        unique_key = f"{cand.get('law_name')}|{cand.get('id')}"
                        if is_match and unique_key not in seen_chunks:
                            filtered_related.append(cand)
                            seen_chunks.add(unique_key)
                    
                    doc["related_documents"] = self._filter_date(filtered_related, k=3, search_date=search_date)
                else:
                    doc["related_documents"] = []
                    
        return top_results