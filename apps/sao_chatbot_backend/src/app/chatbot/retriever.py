from datetime import datetime
from typing import List, Optional
from langchain_core.documents import Document
from langchain_neo4j import Neo4jGraph
from langchain_huggingface import HuggingFaceEmbeddings

class Retriever:
    def __init__(self, uri: str, username: str, password: str):
        self.graph = Neo4jGraph(
            url=uri,
            username=username,
            password=password,
            refresh_schema=False 
        )
        
        print("📥 Loading Embedding Model (BAAI/bge-m3)...")
        self.embeddings = HuggingFaceEmbeddings(
            model_name="BAAI/bge-m3",
            model_kwargs={'device': 'cpu'}, 
            encode_kwargs={'normalize_embeddings': True} 
        )

    def retrieve(self, query: str, query_date: Optional[str] = None, k: int = 5) -> List[Document]:

        results =  {
            "k": k,
            "embedding":"data",
            "date": query_date
        }

        return self._format_results(results, query_date)

    def _format_results(self, results, query_date) -> List[Document]:
        """Converts Neo4j records into LangChain Documents."""
        documents = []
        for r in results:
            # Create a clean metadata dictionary
            metadata = {
                "source": r['source_law'],
                "clause_id": r['clause_id'],
                "clause_label": r['clause_label'],
                "effective_date": str(r['effective_date']),
                "query_date": query_date,
                "score": r['score']
            }
            
            # Create the Document content
            page_content = (
                f"กฎหมาย: {r['source_law']}\n"
                f"ส่วนที่: {r['clause_label']}\n"
                f"มีผลบังคับใช้เมื่อ: {r['effective_date']}\n"
                f"เนื้อหา ({query_date}):\n{r['content']}"
            )
            
            documents.append(Document(page_content=page_content, metadata=metadata))
            
        return documents
