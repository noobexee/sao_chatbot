from src.app.utils.preprocess_dataset import run_indexing_pipeline
import os

INDEX_PATH = "storage/faiss_inde"

if __name__ == "__main__":
    if os.path.exists(INDEX_PATH):
        print("Index found. Skipping ingestion...")
    else:
        print("Creating new index...")
        regulation_path_file = "metadata/ระเบียบ/"
        guideline_path_file = "metadata/แนวทาง/"
        order_path_file = "metadata/คำสั่ง/"
        run_indexing_pipeline("metadata/init")

        run_indexing_pipeline(regulation_path_file)
        run_indexing_pipeline(guideline_path_file)
        run_indexing_pipeline(order_path_file)
