import weaviate
from weaviate.classes.config import Property, DataType


AWS_IP = "localhost"  
PORT = 8080
GRPC_PORT = 50051

def fix_schema():
    print(f"Connecting to AWS Weaviate at {AWS_IP}...")
    
    client = weaviate.connect_to_custom(
        http_host=AWS_IP,
        http_port=PORT,
        http_secure=False,
        grpc_host=AWS_IP,
        grpc_port=GRPC_PORT,
        grpc_secure=False
    )

    try:
        # Get the collection
        if not client.collections.exists("LegalDocument"):
            print("Error: Class 'LegalDocument' does not exist on AWS yet.")
            print("Please run your ingestion script first!")
            return

        legal_docs = client.collections.get("LegalDocument")
        
        # Get current properties
        current_props = [p.name for p in legal_docs.config.get().properties]
        print(f"Current Properties on AWS: {current_props}")

        # --- FIX 1: Add valid_until (The one causing your crash) ---
        if "valid_until" not in current_props:
            print("Adding missing property: 'valid_until' (DATE)...")
            legal_docs.config.add_property(
                Property(name="valid_until", data_type=DataType.DATE)
            )
        else:
            print("'valid_until' exists.")

        # --- FIX 2: Add valid_from ---
        if "valid_from" not in current_props:
            print("Adding missing property: 'valid_from' (DATE)...")
            legal_docs.config.add_property(
                Property(name="valid_from", data_type=DataType.DATE)
            )
        else:
            print("'valid_from' exists.")

        # --- FIX 3: Add doc_type (For filtering) ---
        if "doc_type" not in current_props:
            print("Adding missing property: 'doc_type' (TEXT)...")
            legal_docs.config.add_property(
                Property(name="doc_type", data_type=DataType.TEXT)
            )
        else:
            print("'doc_type' exists.")

        # --- FIX 4: Add law_name (For filtering) ---
        if "law_name" not in current_props:
            print("🛠  Adding missing property: 'law_name' (TEXT)...")
            legal_docs.config.add_property(
                Property(name="law_name", data_type=DataType.TEXT)
            )
        else:
            print("'law_name' exists.")
        
        if "version" not in current_props:
            print("🛠  Adding missing property: 'version' (TEXT)...")
            legal_docs.config.add_property(
                Property(name="version", data_type=DataType.TEXT)
            )
        else:
            print("'version' exists.")

        print("\nSchema patching complete! You can now run retriever.py")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        client.close()

if __name__ == "__main__":
    fix_schema()