from typing import List, Optional, Dict, Any
from datetime import datetime
from pythainlp import word_tokenize
from langchain_core.documents import Document
import numpy as np
from rank_bm25 import BM25Okapi
from src.app.chatbot.utils.embedding import BGEEmbedder
from src.db.vector_store import load_faiss_index, _global_lock
from ..utils import time_execution

class Retriever:
    def __init__(self):
        self.embedder = BGEEmbedder(model_name="BAAI/bge-m3")
        self.reload_resources()

    def reload_resources(self):
        """Reloads FAISS, Metadata, and BM25 under a single lock."""
        with _global_lock:
            print("Reloading retriever resources...")
            self.index, self.metadata_list = load_faiss_index("storage/faiss_index")
            
            # Rebuild the BM25 corpus to match the new metadata
            self.corpus = [ 
                word_tokenize(doc.get("text", "").lower(), engine="newmm") 
                for doc in self.metadata_list
            ]
            self.bm25 = BM25Okapi(self.corpus)
    def filter_search(self, candidates, k, search_date=None):
        if not search_date:
            target_dt = datetime.now()
        else:
            try:
                target_dt = datetime.strptime(search_date, "%Y-%m-%d")
            except ValueError:
                target_dt = datetime.now()

        filtered_results = []

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
    
    def keyword_search(self, query_text: str, k: int) -> List[Dict]:
        tokenized_query = word_tokenize(query_text.lower(), engine="newmm")
        doc_scores = self.bm25.get_scores(tokenized_query)
        
        top_indices = np.argsort(doc_scores)[::-1][:k * 10]
        results = []
        for i, idx in enumerate(top_indices):
            if doc_scores[idx] == 0: continue 
            results.append({"idx": int(idx), "rank": i})
        return results
    
    def vector_search(self, query_text: str, k: int) -> List[Dict]:
        query_vector = self.embedder.embed_query(query_text)
        
        with _global_lock:
            distances, indices = self.index.search(query_vector, k * 10)
            
        results = []
        for i, idx in enumerate(indices[0]):
            if idx == -1: continue
            results.append({"idx": int(idx), "rank": i})
        return results
    
    def hybrid_search(self, query_text: str, k: int = 10, v_weight: float = 0.6):
        fetch_limit = k * 10
        
        vector_results = self.vector_search(query_text, k=fetch_limit)  
        keyword_results = self.keyword_search(query_text, k=fetch_limit) 
        
        rrf_scores = {}
        c = 60  
        
        for item in vector_results:
            idx = item['idx']
            rank = item['rank']
            rrf_scores[idx] = rrf_scores.get(idx, 0) + (v_weight * (1.0 / (rank + c)))

        for item in keyword_results:
            idx = item['idx']
            rank = item['rank']
            rrf_scores[idx] = rrf_scores.get(idx, 0) + ((1 - v_weight) * (1.0 / (rank + c)))

        sorted_indices = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)

        potential_matches = []
        for idx, score in sorted_indices:
            doc_data = self.metadata_list[idx].copy()
            doc_data["hybrid_score"] = score
            potential_matches.append(doc_data)

        return self.filter_search(potential_matches, k)   
     
    async def retrieve(self, user_query: str, history: List = None, k: int = 10, search_date: str = None) -> List[Document] :

        search_result = self.hybrid_search(
            user_query, 
            k, 
        )
        
        return search_result
        
        
        
