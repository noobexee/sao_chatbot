import weaviate
import os

def reset_weaviate():
    client = weaviate.connect_to_local(
        port=8080, 
        grpc_port=50051
    )
    
    print("Deleting 'RAG_Documents' collection...")
    client.collections.delete("RAG_Documents")
    
    print("Database is clean. You can now run ingest.py.")
    client.close()

if __name__ == "__main__":
    reset_weaviate()