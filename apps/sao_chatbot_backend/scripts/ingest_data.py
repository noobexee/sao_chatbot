import os
from src.app.utils.preprocess_dataset import run_indexing_pipeline

REGULATION_INDEX_PATH = "storage/regulations"
OTHERS_INDEX_PATH = "storage/others"

if __name__ == "__main__":
    
    if os.path.exists(f"{REGULATION_INDEX_PATH}") and os.path.exists(f"{OTHERS_INDEX_PATH}"):
        print("Indexes found. Skipping ingestion...")
    else:
        print("Creating new dual indexes...")
        
        os.makedirs(REGULATION_INDEX_PATH, exist_ok=True)
        os.makedirs(OTHERS_INDEX_PATH, exist_ok=True)

        # Cleaned: No more redundant boolean flags!
        run_indexing_pipeline("metadata/ระเบียบ/", is_regulation_folder=True)
        run_indexing_pipeline("metadata/แนวทาง/", is_regulation_folder=False)
        run_indexing_pipeline("metadata/คำสั่ง/", is_regulation_folder=False)
        run_indexing_pipeline("metadata/หลักเกณฑ์/", is_regulation_folder=False)