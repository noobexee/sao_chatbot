import os
import sys
from pathlib import Path

from langchain_text_splitters import RecursiveCharacterTextSplitter
from src.app.llm.ocr import TyphoonOCRLoader
from src.db.vector_store import get_vectorstore

CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CURRENT_DIR.parent
sys.path.append(str(PROJECT_ROOT))
DATA_PATH = os.path.join(PROJECT_ROOT, "data/documents")

def ingest_data():

    if not os.path.exists(DATA_PATH):
        print(f"Error: Data folder not found at {DATA_PATH}")
        return

    all_docs = []
    
    files = [f for f in os.listdir(DATA_PATH) if f.lower().endswith(".pdf")]
    
    if not files:
        print(" No PDF files found.")
        return

    print(f"found {len(files)} PDFs. Processing with Typhoon OCR...")

    for file in files:
        full_path = os.path.join(DATA_PATH, file)
        try:
            loader = TyphoonOCRLoader(full_path)
            docs = loader.load()
            all_docs.extend(docs)
        except Exception as e:
            print(f"Failed to load {file}: {e}")

    if not all_docs:
        print("No documents were successfully loaded.")
        return

    print(f"Splitting {len(all_docs)} documents...")
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000, 
        chunk_overlap=200,
        separators=["\n\n", "\n", " ", ""] 
    )
    chunks = text_splitter.split_documents(all_docs)
    print(f"Generated {len(chunks)} chunks.")
    try:
        vectorstore = get_vectorstore()
    
        vectorstore.add_documents(chunks)
        print("Success! All data ingested.")
        
    except Exception as e:
        print(f"Database Upload Failed: {e}")

if __name__ == "__main__":
    ingest_data()