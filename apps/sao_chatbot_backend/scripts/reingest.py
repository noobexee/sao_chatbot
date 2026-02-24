# scripts/reingest.py
import shutil
import os
from scripts.ingest_data import run_indexing_pipeline 

INDEX_PATH = "storage/faiss_index"

def reset_and_ingest():
    if os.path.exists(INDEX_PATH):
        print(f"Removing old index at {INDEX_PATH}...")
        shutil.rmtree(INDEX_PATH)
    
    os.makedirs(INDEX_PATH, exist_ok=True)
    
    print("Starting fresh ingestion...")
    regulation_path_file = "metadata/ระเบียบ/"
    guideline_path_file = "metadata/แนวทาง/"
    order_path_file = "metadata/คำสั่ง/"
    run_indexing_pipeline("metadata/init")

    run_indexing_pipeline(regulation_path_file)
    run_indexing_pipeline(guideline_path_file)
    run_indexing_pipeline(order_path_file)

if __name__ == "__main__":
    reset_and_ingest()