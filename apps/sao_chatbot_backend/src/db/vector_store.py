import os
import weaviate
from langchain_weaviate.vectorstores import WeaviateVectorStore
from langchain_huggingface import HuggingFaceEmbeddings

def get_vectorstore():
    weaviate_host = os.getenv("WEAVIATE_HOST", "vector_db")
    weaviate_port = int(os.getenv("WEAVIATE_PORT", 8080))
    weaviate_grpc_port = int(os.getenv("WEAVIATE_GRPC_PORT", 50051))

    client = weaviate.connect_to_custom(
        http_host=weaviate_host,
        http_port=weaviate_port,
        http_secure=False,
        grpc_host=weaviate_host,
        grpc_port=weaviate_grpc_port,
        grpc_secure=False,
    )

    embeddings = HuggingFaceEmbeddings(
        model_name="BAAI/bge-m3",
        model_kwargs={'device': 'cpu'}, 
        encode_kwargs={'normalize_embeddings': True} 
    )

    return WeaviateVectorStore(
        client=client,
        index_name="RAG_Documents",
        text_key="text",
        embedding=embeddings
    )