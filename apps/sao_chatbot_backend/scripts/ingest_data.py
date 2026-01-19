import json
import re
import weaviate
from pathlib import Path
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_weaviate.vectorstores import WeaviateVectorStore
from langchain_core.documents import Document


DATA_DIRS = [
    Path("data"),                          
    Path("data/คำสั่ง"),                  
    Path("data/แนวทางการตรวจสอบ CA")       
]

METADATA_FILE = "metadata.json"
WEAVIATE_URL = "localhost"
WEAVIATE_PORT = 8080
WEAVIATE_GRPC = 50051
EMBEDDING_MODEL = "BAAI/bge-m3"
INDEX_NAME = "LegalDocument"

def load_metadata_map(json_path):
    path = Path(json_path)
    if not path.exists():
        raise FileNotFoundError(f"CRITICAL: Could not find {json_path}. Please run the metadata extraction scripts first.")
    
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def chunk_by_double_enter(text: str, source_file: str):

    chunks = [c.strip() for c in re.split(r"\n\s*\n", text) if c.strip()]
    documents = []
    
    for i, chunk in enumerate(chunks, start=1):
        documents.append(
            Document(
                page_content=chunk,
                metadata={
                    "source": source_file,
                }
            )
        )
    return documents

def main():
    print(f"Loading metadata from {METADATA_FILE}...")
    try:
        metadata_map = load_metadata_map(METADATA_FILE)
        print(f"Loaded metadata for {len(metadata_map)} files.")
    except Exception as e:
        print(e)
        return

    all_documents = []
    files_processed = 0
    files_skipped = 0

    print("Scanning directories...")
    for folder in DATA_DIRS:
        if not folder.exists():
            print(f"Warning: Folder not found: {folder}")
            continue

        txt_files = list(folder.glob("*.txt"))
        print(f"Checking {folder}: Found {len(txt_files)} .txt files")

        for file_path in txt_files:
            filename = file_path.name

            if filename not in metadata_map:
                print(f"Skipping '{filename}' - No metadata found in JSON.")
                files_skipped += 1
                continue


            meta = metadata_map[filename]

            try:
                raw_text = file_path.read_text(encoding="utf-8")
                chunks = chunk_by_double_enter(raw_text, filename)

                for doc in chunks:
                    doc.metadata["law_name"] = meta["law_name"]
                    doc.metadata["doc_type"] = meta["doc_type"]
                    doc.metadata["version"] = meta["version"]
                    
                    eff = meta["effective"]
                    exp = meta["expire"]
                    
                    doc.metadata["valid_from"] = eff if "T" in eff else f"{eff}T00:00:00Z"
                    doc.metadata["valid_until"] = exp if "T" in exp else f"{exp}T23:59:59Z"

                all_documents.extend(chunks)
                files_processed += 1
                
            except Exception as e:
                print(f" Error reading {filename}: {e}")

    print(f"Processing Summary:")
    print(f"   - Files Processed: {files_processed}")
    print(f"   - Files Skipped:   {files_skipped}")
    print(f"   - Total Chunks:    {len(all_documents)}")

    if len(all_documents) == 0:
        print("No documents to ingest. Exiting.")
        return

    print("\nConnecting to Weaviate...")
    client = weaviate.connect_to_local(
        host=WEAVIATE_URL,
        port=WEAVIATE_PORT,
        grpc_port=WEAVIATE_GRPC
    )

    print(f"Loading Embedding Model ({EMBEDDING_MODEL})...")
    embeddings = HuggingFaceEmbeddings(
        model_name=EMBEDDING_MODEL,
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True}
    )

    print("Ingesting documents... (This may take a moment)")
    try:
        vectorstore = WeaviateVectorStore.from_documents(
            client=client,
            documents=all_documents,
            embedding=embeddings,
            index_name=INDEX_NAME
        )
        print("Ingestion Successfully Completed!")
        
    except Exception as e:
        print(f"Error during Weaviate ingestion: {e}")
    finally:
        client.close()

if __name__ == "__main__":
    main()