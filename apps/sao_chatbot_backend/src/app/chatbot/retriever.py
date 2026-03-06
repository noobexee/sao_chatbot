import re
import os 
import json
import logging
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime
from pythainlp import word_tokenize
import numpy as np
from rank_bm25 import BM25Okapi
from src.app.utils.embedding import BGEEmbedder, global_embedder
from src.db.vector_store.vector_store import load_faiss_index 
from src.app.llm.typhoon import TyphoonLLM
from .utils.formatters import simplify_thai_text, thai_to_arabic, normalize_regulation_id
import asyncio
from threading import Lock

REGULATION_PATH = "storage/regulations"
OTHERS_PATH = "storage/others"

logger = logging.getLogger(__name__)

class Retriever:
    def __init__(self):
        self.embedder = global_embedder
        self.llm = TyphoonLLM().get_model()
        
        self.reg_index = None
        self.reg_metadata = []
        self.reg_bm25 = None

        self.other_index = None
        self.other_metadata = []
        self.other_bm25 = None

        self.master_map = self._load_master_map("storage/master_map.json")
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
        
    def _boost_by_title(self, candidates: List[Dict], keywords: List[str]) -> List[Dict]:
        """
        Artificially boosts the score of candidates if the user's keywords 
        appear in the document's title (law_name).
        """
        try : 
            for cand in candidates:
                law_name = cand.get("law_name", "").lower()
                if not law_name: 
                    continue
                
                overlap = sum(1 for kw in keywords if kw.lower() in law_name)
                
                if overlap > 0:
                    current_score = cand.get("hybrid_score", 0)
                    cand["hybrid_score"] = current_score + (overlap * 0.05)
                
            return sorted(candidates, key=lambda x: x.get("hybrid_score", 0), reverse=True)
        except :
            return candidates
    
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
            
            # Clean up common LLM artifacts
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
            target_dt = now.replace(year=now.year + 543)
        else:
            try:
                target_dt = datetime.strptime(search_date, "%Y-%m-%d")
            except ValueError:
                now = datetime.now() 
                target_dt = now.replace(year=now.year + 543)

        filtered_results = []
        seen_ids = set()

        for match in candidates:
            try :
                law_name = match.get("law_name", "")
                chunk_id = match.get("id") or match.get("document_id", "")
                unique_key = f"{law_name}|{chunk_id}"
                
                if unique_key in seen_ids: 
                    continue

                eff_raw = match.get("effective_date")
                exp_raw = match.get("expire_date")

                if not eff_raw or str(eff_raw).strip().lower() == "null":
                    eff_str = "1000-01-01"
                else:
                    eff_str = str(eff_raw).strip()

                if not exp_raw or str(exp_raw).strip().lower() == "null":
                    exp_str = "9999-12-31"
                else:
                    exp_str = str(exp_raw).strip()
                
                try:
                    eff_dt = datetime.strptime(eff_str, "%Y-%m-%d")
                    exp_dt = datetime.strptime(exp_str, "%  Y-%m-%d")
                except ValueError:
                    eff_dt = datetime.strptime("1000-01-01", "%Y-%m-%d")
                    exp_dt = datetime.strptime("9999-12-31", "%Y-%m-%d")

                if eff_dt <= target_dt <= exp_dt:
                    filtered_results.append(match)
                    seen_ids.add(unique_key)
            except Exception as e:
                logger.debug(f"Skipping candidate {match.get('id')} due to date error: {e}")
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
    
    async def _retrieve_other_by_type(self, query: str, target_doc_type: str, k: int = 3, search_date: str = None, history: list = []):
        try : 
            effective_query = await self._rewrite_query_with_history(query, history)
            keywords = await self.extract_keywords(effective_query)
            
            fetch_k = k * 5 
            vec_res = self.vector_search_other(effective_query, fetch_k)
            key_res = self.keyword_search_other(keywords, fetch_k)
            
            candidates = self._run_rrf_fusion(vec_res, key_res, self.other_metadata, fetch_k)
            boosted_candidates = self._boost_by_title(candidates, keywords)
            
            filtered_by_type = []
            seen_chunks = set()
            for cand in boosted_candidates:
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
            reg_results = await self.hybrid_search_regulation(effective_query, k, search_date)
            keywords = await self.extract_keywords(effective_query)

            for reg in reg_results:
                try:
                    allowed_titles = self.get_related_document_titles(reg)
                    if not allowed_titles:
                        reg["related_documents"] = []
                        continue

                    normalized_allowed = [simplify_thai_text(t) for t in allowed_titles]
                    
                    # Parallel search for related documents
                    vec_task = asyncio.to_thread(self.vector_search_other, effective_query, 20)
                    key_task = asyncio.to_thread(self.keyword_search_other, keywords, 20)
                    vec_res, key_res = await asyncio.gather(vec_task, key_task)
                    
                    candidates = self._run_rrf_fusion(vec_res, key_res, self.other_metadata, 20)

                    filtered_related = []
                    seen_chunks = set()
                    for cand in candidates:
                        norm_cand_name = simplify_thai_text(cand.get("law_name", ""))
                        is_match = any(nt in norm_cand_name or norm_cand_name in nt for nt in normalized_allowed)
                        unique_key = f"{cand.get('law_name')}|{cand.get('id')}"
                        if is_match and unique_key not in seen_chunks:
                            filtered_related.append(cand)
                            seen_chunks.add(unique_key)
                    
                    reg["related_documents"] = self._filter_date(filtered_related, k=k, search_date=search_date)
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
        
            reg_task = self.hybrid_search_regulation(effective_query, k=k*2, search_date=search_date)
            other_task = self.hybrid_search_other(effective_query, k=k*2, search_date=search_date)
            
            reg_candidates, other_candidates = await asyncio.gather(reg_task, other_task)
            all_candidates = (reg_candidates or []) + (other_candidates or [])
            
            for cand in all_candidates:
                try:
                    law_name = cand.get("law_name") or ""
                    doc_type = cand.get("doc_type") or ""
                    score = cand.get("hybrid_score", 0)
                    
                    if "ระเบียบ" in doc_type or "ระเบียบ" in law_name: score *= 1.30  
                    elif "คำสั่ง" in doc_type or "คำสั่ง" in law_name: score *= 1.10  
                    elif "หลักเกณฑ์" in doc_type or "หลักเกณฑ์" in law_name: score *= 1.05  
                    cand["hybrid_score"] = score
                except Exception:
                    continue
                    
            all_candidates.sort(key=lambda x: x.get("hybrid_score", 0), reverse=True)
            top_results = all_candidates[:k]
            
            keywords = await self.extract_keywords(effective_query)
            for doc in top_results:
                if "ระเบียบ" in (doc.get("law_name") or ""):
                    try:
                        allowed_titles = self.get_related_document_titles(doc)
                        if allowed_titles:
                            normalized_allowed = [simplify_thai_text(t) for t in allowed_titles]
                            vec_res = self.vector_search_other(effective_query, k=15)
                            key_res = self.keyword_search_other(keywords, k=15)
                            other_cands = self._run_rrf_fusion(vec_res, key_res, self.other_metadata, k=15)
                            
                            filtered_related = []
                            seen_chunks = set()
                            for cand in other_cands:
                                norm_cand_name = simplify_thai_text(cand.get("law_name", ""))
                                is_match = any(nt in norm_cand_name or norm_cand_name in nt for nt in normalized_allowed)
                                unique_key = f"{cand.get('law_name')}|{cand.get('id')}"
                                if is_match and unique_key not in seen_chunks:
                                    filtered_related.append(cand)
                                    seen_chunks.add(unique_key)
                            doc["related_documents"] = self._filter_date(filtered_related, k=3, search_date=search_date)
                        else:
                            doc["related_documents"] = []
                    except Exception as e:
                        logger.debug(f"Could not link related docs in general search: {e}")
                        doc["related_documents"] = []
            return top_results
        except Exception as e:
            logger.error(f"Top-level retrieve_general failed: {e}")
            return []