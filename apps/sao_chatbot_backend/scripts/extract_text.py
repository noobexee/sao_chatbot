import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from unittest.mock import MagicMock

CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CURRENT_DIR.parent 
sys.path.append(str(PROJECT_ROOT))

mock_vector_store = MagicMock()
sys.modules["src.db.vector_store"] = mock_vector_store

try:
    from src.app.llm.ocr import TyphoonOCRLoader
except ImportError:
    sys.path.append(str(CURRENT_DIR))
    from src.app.llm.ocr import TyphoonOCRLoader
load_dotenv()

INPUT_DIR = Path("data/documents") 
OUTPUT_DIR = Path("data/raw_text")

def process_documents():
    if not INPUT_DIR.exists():
        print(f"Error: Input directory '{INPUT_DIR}' not found.")
        return
    pdf_files = list(INPUT_DIR.rglob("*.pdf"))
    
    if not pdf_files:
        print("No PDF files found in data/documents or its subfolders")
        return

    print(f"Found {len(pdf_files)} PDF files. Processing with TyphoonOCRLoader...")

    for file_path in pdf_files:
        try:
            print(f"Processing: {file_path.name}...")
            relative_path = file_path.relative_to(INPUT_DIR)

            output_filename = relative_path.with_suffix(".md")
            
            output_path = OUTPUT_DIR / output_filename
            output_path.parent.mkdir(parents=True, exist_ok=True)

            loader = TyphoonOCRLoader(str(file_path))
            docs = loader.load()

            if not docs:
                print(f"No content extracted from {file_path.name}")
                continue
                
            combined_text = "\n\n".join([doc.page_content for doc in docs])

            with open(output_path, "w", encoding="utf-8") as f:
                f.write(combined_text)
            
            print(f"Saved to: {output_path}")

        except Exception as e:
            print(f"Error processing {file_path.name}: {e}")

if __name__ == "__main__":
    process_documents()