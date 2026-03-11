import re
import os 
import json
import logging
from typing import List, Dict, Any, Tuple
from datetime import datetime
from pythainlp import word_tokenize
import numpy as np
from rank_bm25 import BM25Okapi
from src.app.llm.llm_manager import get_llm
from src.app.utils.embedding import global_embedder
from src.db.vector_store.vector_store import load_faiss_index 
from src.app.chatbot.utils.formatters import simplify_thai_text, thai_to_arabic, normalize_regulation_id
import asyncio
from threading import Lock
from flashrank import Ranker, RerankRequest 

REGULATION_PATH = "storage/regulations"
OTHERS_PATH = "storage/others"

logger = logging.getLogger(__name__)

class Retriever:
    def __init__(self):
        self.embedder = global_embedder
        self.llm_service = get_llm() 
        self.llm = self.llm_service.get_model()
        
        self.reg_index = None
        self.reg_metadata = []
        self.reg_bm25 = None

        self.other_index = None
        self.other_metadata = []
        self.other_bm25 = None

        self.master_map = self._load_master_map("storage/master_map.json")
        self.source_map = self._load_master_map("storage/master_map.json")
        self.search_lock = Lock()
        self._reload_resources()

    def _reload_resources(self):
        print("Reloading retriever resources...") 
        self.reg_index, self.reg_metadata, self.reg_bm25 = self._load_store(REGULATION_PATH)
        self.other_index, self.other_metadata, self.other_bm25 = self._load_store(OTHERS_PATH)
    
    def _load_master_map(self, path: str) -> Dict:
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
 
    def _load_store(self, path: str) -> Tuple[Any, List, Any]:
        try:
            index, metadata = load_faiss_index(path)
            
            if not metadata:
                logger.warning(f"No metadata found at {path}")
                return index, [], None

            corpus = []
            for i, doc in enumerate(metadata):
                try:
                    text = str(doc.get("text", "")).lower()
                    if text.strip():
                        tokens = word_tokenize(text, engine="newmm")
                        corpus.append(tokens)
                    else:
                        corpus.append(["empty"]) 
                except Exception as e:
                    logger.error(f"Failed to tokenize document at index {i} in {path}: {e}")
                    corpus.append(["error"])

            bm25 = BM25Okapi(corpus) if corpus else None
            return index, metadata, bm25

        except Exception as e:
            # This catches "The file doesn't exist" or "FAISS index is corrupted"
            logger.critical(f"FATAL: Could not load search resources at {path}. Error: {e}")
            return None, [], None
  
    async def _rewrite_query_with_history(self, query: str, history: List[Dict[str, str]]) -> str:

        if not history:
            return query

        recent_history = history[-4:] 
        context_str = ""
        for msg in recent_history:
            if hasattr(msg, 'content'): 
                role = "User" if msg.type == "human" else "Assistant"
                content = msg.content
            elif isinstance(msg, dict):
                role = "User" if msg.get('role') == 'user' else "Assistant"
                content = msg.get('content', '')
            else:
                continue
        context_str += f"{role}: {content}\n"

        prompt = f"""
        You are a Thai Legal Search Assistant. Your task is to rewrite the "Follow-up Query" 
        into a standalone Thai search query that is descriptive and includes all relevant 
        entities from the Chat History.

        RULES:
        1. Preserve Law Names: If a law was mentioned (e.g., "ระเบียบการจัดซื้อ"), include it.
        2. Preserve Identifiers: Keep version numbers (ฉบับที่...), years (พ.ศ....), and sections (ข้อ/มาตรา...).
        3. De-reference Pronouns: Change words like "อันนี้", "อันที่สอง", "ข้อนี้" into the actual names.
        4. Keep it Concise: Return ONLY the rewritten Thai query string.

        Chat History:
        {context_str}

        Follow-up Query: {query}
        Standalone Thai Query:"""

        try:
            response = await self.llm.ainvoke(prompt)
            rewritten = response.content.strip() if hasattr(response, 'content') else str(response)
            
            rewritten = rewritten.replace('"', '').replace("Query:", "").strip()
            
            return rewritten if rewritten else query
        
        except Exception as e:
            print(f"Query rewriting error: {e}")
            return query   
        
    async def extract_keywords(self, query_text: str) -> List[str]:
        """
        Extracts Thai legal keywords using an English prompt for better 
        instruction adherence and logical extraction of government entities.
        """
        prompt = f"""
        You are a Thai Legal Search Expert. Your task is to extract search keywords 
        from a user's query to be used in a BM25 keyword search engine.

        EXTRACTION RULES:
        1. PRIORITIZE Entities: Always extract Government Ministries (กระทรวง) and Departments (กรม).
        2. IDENTIFY Actions: Extract core legal actions or subjects (e.g., เรื่องร้องเรียน, การใช้จ่ายเงิน).
        3. NO EXPLANATIONS: Return ONLY a comma-separated list of Thai keywords.
        4. PRESERVE Format: Keep Thai terminology exactly as written in the query.

        EXAMPLES:
        Query: "เรื่องร้องเรียนเกี่ยวกับการใช้จ่ายเงินของกรมการปกครอง กระทรวงมหาดไทย"
        Keywords: กระทรวงมหาดไทย, กรมการปกครอง, เรื่องร้องเรียน, การใช้จ่ายเงิน

        Query: "หลักเกณฑ์พัสดุของสำนักงานปลัดสำนักนายกรัฐมนตรี"
        Keywords: สำนักงานปลัดสำนักนายกรัฐมนตรี, หลักเกณฑ์พัสดุ

        USER QUERY: "{query_text}"
        KEYWORDS:"""
        
        try:
            response = await self.llm.ainvoke(prompt)
            raw_text = response.content.strip() if hasattr(response, 'content') else str(response)
            
            keywords = [k.strip() for k in re.split(r'[,|\n]', raw_text) if k.strip()]
            
            keywords = [re.sub(r'^(Keywords|คำสำคัญ):\s*', '', k, flags=re.IGNORECASE).strip() for k in keywords]

            if not keywords:
                return word_tokenize(query_text, engine="newmm")
                
            return keywords
        
        except Exception as e:
            logger.error(f"Keyword extraction failed for '{query_text}': {e}")
            # Return base tokens so the BM25 search still functions
            return word_tokenize(query_text, engine="newmm")
    
    def _filter_date(self, candidates, k, search_date=None):
        if not search_date:
            now = datetime.now()
            target_dt = datetime(now.year + 543, now.month, now.day)
        else:
            try:
                target_dt = datetime.strptime(search_date, "%Y-%m-%d")
            except ValueError:
                now = datetime.now()
                target_dt = datetime(now.year + 543, now.month, now.day)

        filtered_results = []
        seen_ids = set()

        for match in candidates:
            try:
                law_name = match.get("law_name", "")
                chunk_id = match.get("id") or match.get("document_id", "")
                unique_key = f"{law_name}|{chunk_id}"
                
                if unique_key in seen_ids: 
                    continue

                eff_raw = match.get("effective_date")
                exp_raw = match.get("expire_date")

                def parse_thai_date(val, is_expiry=False):
                    if val is None:
                        return datetime(9999, 12, 31) if is_expiry else datetime(1000, 1, 1)
                    
                    s_val = str(val).strip().lower()
                    if s_val in ["", "none", "null", "nan"]:
                        return datetime(9999, 12, 31) if is_expiry else datetime(1000, 1, 1)
                    
                    return datetime.strptime(s_val, "%Y-%m-%d")

                eff_dt = parse_thai_date(eff_raw, is_expiry=False)
                exp_dt = parse_thai_date(exp_raw, is_expiry=True)

                if eff_dt <= target_dt <= exp_dt:
                    filtered_results.append(match)
                    seen_ids.add(unique_key)
        
            except Exception as e:
                logger.error(f"Error filtering {unique_key}: {e}")
                continue

            if len(filtered_results) >= k:
                break
                
        return filtered_results
    
    def _run_rrf_fusion(self, vector_results, keyword_results, metadata_list, k, v_weight=0.5):
        """Combines results using Reciprocal Rank Fusion."""
        try :
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
        except Exception as e:
            logger.error(f"RRF Fusion error: {e}")
            return []

    def get_parent_regulations(self, other_doc: Dict) -> List[Dict[str, Any]] :
        try:
            if not self.source_map:
                return []

            doc_title = other_doc.get("law_name", "").strip()
            parent_references = []

            if doc_title in self.source_map:
                mapping_values = self.source_map[doc_title]
                
                for entry in mapping_values:
                    if ":" in entry:
                        name_part, section_part = entry.split(":", 1)
                        parent_references.append({
                            "reg_name": name_part.strip(),
                            "section": section_part.strip()
                        })
                    else:
                        parent_references.append({
                            "reg_name": entry.strip(),
                            "section": ""
                        })
            return parent_references
        except Exception as e:
            logger.error(f"Error in get_parent_regulations: {e}")
            return []
    
    def get_related_document_titles(self, reg_doc: Dict) -> List[str]:
        try : 
            if not self.master_map: return []
            full_law_name = reg_doc.get("law_name", "")
            core_law = re.sub(r'\(ฉบับที่.*?\)|พ\.ศ\..*$', '', full_law_name).strip()
            norm_core_law = simplify_thai_text(core_law)

            law_mapping = {}
            for map_law_name, clauses in self.master_map.items():
                if norm_core_law in simplify_thai_text(map_law_name) or simplify_thai_text(map_law_name) in norm_core_law:
                    law_mapping = clauses
                    break
            
            if not law_mapping: return []

            reg_id_digits = re.findall(r'[๐-๙0-9]+', normalize_regulation_id(reg_doc.get("id", "")))
            base_num = thai_to_arabic(reg_id_digits[0]) if reg_id_digits else ""
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
        
        except Exception as e:
            logger.warning(f"Error mapping related titles for doc {reg_doc.get('id')}: {e}")
            return []
    
    def _is_exact_regulation_match(self, target_name: str, target_section_raw: str, reg_meta: Dict) -> bool:
        if target_name not in reg_meta.get("law_name", ""):
            return False
            
        if not target_section_raw:
            return True 
            
        target_section_norm = normalize_regulation_id(target_section_raw)
        meta_id_norm = normalize_regulation_id(reg_meta.get("id", ""))
        
        t_base_match = re.search(r'(ข้อ\s*\d+)', target_section_norm)
        t_base = t_base_match.group(1) if t_base_match else target_section_norm.split()[0]
        
        m_base_match = re.search(r'(ข้อ\s*\d+)', meta_id_norm)
        m_base = m_base_match.group(1) if m_base_match else meta_id_norm.split('_')[0]
        
        if t_base != m_base:
            return False
            
        t_sub_match = re.search(r'\(\d+\)', target_section_norm)
        if t_sub_match:
            t_sub = t_sub_match.group(0)
            text_content = reg_meta.get("text", "")
            t_sub_thai = t_sub.translate(str.maketrans('0123456789', '๐๑๒๓๔๕๖๗๘๙'))
            
            if t_sub not in text_content and t_sub_thai not in text_content:
                return False 
                
        return True

    def fetch_exact_parent_regulations(self, cand: Dict, search_date: str = None) -> List[Dict]:
        parents = self.get_parent_regulations(cand)
        if not parents:
            return []
            
        matched_parents = []
        for p in parents:
            target_name = p.get("reg_name", "")
            target_section = p.get("section", "")
            
            for reg_meta in self.reg_metadata:
                if self._is_exact_regulation_match(target_name, target_section, reg_meta):
                    matched_parents.append(reg_meta)
                    
        return self._filter_date(matched_parents, k=3, search_date=search_date)  
    
    async def fetch_related_other_documents(self, reg: Dict, effective_query: str, keywords: List[str], seen_in_related: set, search_date: str = None, k=5) -> List[Dict]:
        try:
            allowed_titles = self.get_related_document_titles(reg)
            if not allowed_titles:
                return []

            normalized_allowed = [simplify_thai_text(t) for t in allowed_titles]
            
            vec_res = self.vector_search_other(effective_query, k=k*3)
            key_res = self.keyword_search_other(keywords, k=k*3)
            other_cands = self._run_rrf_fusion(vec_res, key_res, self.other_metadata, k=k*3)
            
            filtered_related = []
            for cand in other_cands:
                norm_cand_name = simplify_thai_text(cand.get("law_name", ""))
                is_match = any(nt in norm_cand_name or norm_cand_name in nt for nt in normalized_allowed)
                
                if is_match:
                    unique_key = f"{cand.get('law_name')}|{cand.get('id')}"
                    filtered_related.append(cand)
                    seen_in_related.add(unique_key) 
            
            return self._filter_date(filtered_related, k=3, search_date=search_date)
        except Exception as e:
            logger.debug(f"Error mapping related docs to regulation: {e}")
            return []
    def vector_search_regulation(self, query_text: str, k: int) -> List[Dict]:
        """Performs vector search with error handling for FAISS and Embedding failures."""
        if not self.reg_index: 
            logger.warning("Regulation index not loaded.")
            return []
        
        try:
            vec = self.embedder.embed_query(query_text)
            query_array = np.atleast_2d(vec).astype('float32')
            D, I = self.reg_index.search(query_array, k * 5)
            return [{"idx": int(idx), "rank": i} for i, idx in enumerate(I[0]) if idx != -1]
        except Exception as e:
            logger.error(f"Vector search failed for regulations: {e}")
            return []

    def keyword_search_regulation(self, keyword_list: List[str], k: int) -> List[Dict]:
        """Performs BM25 search with safety checks for tokenization issues."""
        if not self.reg_bm25 or not keyword_list: 
            return []
            
        try:
            tokens = []
            for p in keyword_list: 
                tokens.extend(word_tokenize(p.lower(), engine="newmm"))
            
            if not tokens:
                return []
                
            scores = self.reg_bm25.get_scores(tokens)
            top_idx = np.argsort(scores)[::-1][:k * 5]
            return [{"idx": int(i), "rank": r} for r, i in enumerate(top_idx) if scores[i] > 0]
        except Exception as e:
            logger.error(f"Keyword search (BM25) for regulation failed: {e}")
            return []

    async def hybrid_search_regulation(self, query: str, k: int = 5, search_date: str = None):
        try:
            keywords = await self.extract_keywords(query)
            vec_res = self.vector_search_regulation(query, k)
            key_res = self.keyword_search_regulation(keywords, k)
            candidates = self._run_rrf_fusion(vec_res, key_res, self.reg_metadata, k)
            return self._filter_date(candidates, k, search_date)

        except Exception as e:
            logger.error(f"hybrid search on regulation failed: {e}")
            return []

    def vector_search_other(self, query_text: str, k: int) -> List[Dict]:
        try : 
            if not self.other_index: return []
            vec = self.embedder.embed_query(query_text)
            query_array = np.atleast_2d(vec).astype('float32')
            D, I = self.other_index.search(query_array, k * 5)
            return [{"idx": int(idx), "rank": i} for i, idx in enumerate(I[0]) if idx != -1]
        except Exception as e:
            logger.error(f"Vector search failed for non regulation type: {e}")
            return []

    def keyword_search_other(self, keyword_list: List[str], k: int) -> List[Dict]:
        try : 
            if not self.other_bm25 or not keyword_list: return []
            tokens = []
            for p in keyword_list: tokens.extend(word_tokenize(p.lower(), engine="newmm"))
            scores = self.other_bm25.get_scores(tokens)
            top_idx = np.argsort(scores)[::-1][:k * 5]
            return [{"idx": int(i), "rank": r} for r, i in enumerate(top_idx) if scores[i] > 0]
        except Exception as e:
            logger.error(f"Keyword search (BM25) for non regulation failed: {e}")
            return []

    async def hybrid_search_other(self, query: str, k: int = 5, search_date: str = None):
        try:
            keywords = await self.extract_keywords(query)
            vec_res = self.vector_search_other(query, k)
            key_res = self.keyword_search_other(keywords, k)
            candidates = self._run_rrf_fusion(vec_res, key_res, self.other_metadata, k)
            return self._filter_date(candidates, k, search_date)
        except Exception as e:
            logger.error(f"hybrid search on non regulation failed: {e}")
            return []
  
    async def _retrieve_other_by_type(self, query: str, target_doc_type: str, k: int = 3, search_date: str = None, history: list = []):
        try : 
            effective_query = await self._rewrite_query_with_history(query, history)
            keywords = await self.extract_keywords(effective_query)
            
            fetch_k = k * 5 
            vec_res = self.vector_search_other(effective_query, fetch_k)
            key_res = self.keyword_search_other(keywords, fetch_k)
            
            candidates = self._run_rrf_fusion(vec_res, key_res, self.other_metadata, fetch_k)
            
            filtered_by_type = []
            seen_chunks = set()
            for cand in candidates:
                if target_doc_type not in cand.get("doc_type", ""): continue
                unique_key = f"{cand.get('law_name')}|{cand.get('id')}"
                if unique_key not in seen_chunks:
                    filtered_by_type.append(cand)
                    seen_chunks.add(unique_key)
                    
            return self._filter_date(filtered_by_type, k=k, search_date=search_date)
        except Exception as e:
            logger.warning(f"Error retrieving non regulation document: {e}")
            return []

    async def retrieve_order(self, user_query: str, k: int = 3, history: list = [], search_date: str = None):
        return await self._retrieve_other_by_type(user_query, "คำสั่ง", k, search_date, history)

    async def retrieve_guideline(self, user_query: str, k: int = 3, history: list = [], search_date: str = None):
        return await self._retrieve_other_by_type(user_query, "แนวทาง", k, search_date, history)

    async def retrieve_standard(self, user_query: str, k: int = 3, history: list = [], search_date: str = None):
        return await self._retrieve_other_by_type(user_query, "หลักเกณฑ์", k, search_date, history)
    
    async def retrieve_regulation(self, user_query: str, k: int = 3, history: list = [], search_date: str = None):
        try:
            effective_query = await self._rewrite_query_with_history(user_query, history)
            keywords = await self.extract_keywords(effective_query)
            
            reg_results = await self.hybrid_search_regulation(effective_query, k, search_date)

            seen_in_related = set()
            for reg in (reg_results or []):
                try:
                    reg["related_documents"] = await self.fetch_related_other_documents(
                        reg, effective_query, keywords, seen_in_related, search_date
                    )
                except Exception as e:
                    logger.error(f"Failed to fetch related documents for reg {reg.get('id')}: {e}")
                    reg["related_documents"] = []
                    
            return reg_results
            
        except Exception as e:
            logger.error(f"Top-level retrieve_regulation failed: {e}")
            return []
        
    async def retrieve_general(self, query: str, k: int = 3, history: list = [], search_date: str = None):
        try:
            effective_query = await self._rewrite_query_with_history(query, history)
        
            reg_task = self.hybrid_search_regulation(effective_query, k=k*3, search_date=search_date)
            other_task = self.hybrid_search_other(effective_query, k=k*3, search_date=search_date)
            
            reg_candidates, other_candidates = await asyncio.gather(reg_task, other_task)

            keywords = await self.extract_keywords(effective_query)
            seen_in_related = set()
            
            seen_in_related = set()
            for reg in (reg_candidates or []):
                reg["related_documents"] = await self.fetch_related_other_documents(
                    reg, effective_query, keywords, seen_in_related, search_date
                )

            final_other_candidates = []
            for cand in (other_candidates or []):
                unique_key = f"{cand.get('law_name')}|{cand.get('id')}"
                if unique_key not in seen_in_related:
                    cand["related_documents"] = self.fetch_exact_parent_regulations(cand, search_date)
                    final_other_candidates.append(cand)

            all_candidates = (reg_candidates or []) + final_other_candidates
            
            for cand in all_candidates:
                law_name, doc_type = cand.get("law_name") or "", cand.get("doc_type") or ""
                score = cand.get("hybrid_score", 0)
                
                if "ระเบียบ" in doc_type or "ระเบียบ" in law_name: score *= 1.30  
                elif "คำสั่ง" in doc_type or "คำสั่ง" in law_name: score *= 1.10  
                elif "หลักเกณฑ์" in doc_type or "หลักเกณฑ์" in law_name: score *= 1.05  
                
                cand["hybrid_score"] = score
                        
            all_candidates.sort(key=lambda x: x.get("hybrid_score", 0), reverse=True)
            return all_candidates[:k]

        except Exception as e:
            logger.error(f"Top-level retrieve_general failed: {e}")
            return []