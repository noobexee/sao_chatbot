import weaviate
import os

def reset_weaviate():
    client = weaviate.connect_to_local(
        port=8080, 
        grpc_port=50051
    )
    
    print("Deleting 'LegalDocument' collection...")
    client.collections.delete("LegalDocument")
    
    print("Database is clean.")
    client.close()

if __name__ == "__main__":
    reset_weaviate()