import os
import json
from pathlib import Path
import numpy as np
from src.app.chatbot.utils.embedding import BGEEmbedder
from src.db.vector_store import create_faiss_index, save_faiss_index, add_embeddings_to_index, load_faiss_index

VECTOR_STORE_DIR = "storage/faiss_index"

def index_single_json_file(file_path: str, embedder: BGEEmbedder):
    """
    Core function: Embeds one JSON file and appends it to the existing FAISS index.
    """
    print(f"Processing single file: {file_path}")
    
    # 1. Load the specific JSON file
    with open(file_path, 'r', encoding='utf-8') as f:
        chunks = json.load(f)
    
    texts = [c['text'] for c in chunks]
    
    new_embeddings = embedder.embed_texts(texts, batch_size=16)
    
    try:
        index, existing_metadata = load_faiss_index(VECTOR_STORE_DIR)
        print("Existing index loaded for update.")
    except FileNotFoundError:
        print("No existing index found. Creating new index...")
        index = create_faiss_index(embedder.embedding_dimension)
        existing_metadata = []

    updated_metadata = add_embeddings_to_index(index, new_embeddings, chunks)
    full_metadata = existing_metadata + updated_metadata
    
    save_faiss_index(index, full_metadata, VECTOR_STORE_DIR)
    print(f"File {os.path.basename(file_path)} indexed and saved.")

def run_indexing_pipeline(metadata_folder: str):
    """
    Bulk function: Clears/Initializes the index and processes every file in the folder.
    """
    print(f"\nStarting Bulk Indexing for Folder: {metadata_folder}")
    embedder = BGEEmbedder()
    
    json_files = list(Path(metadata_folder).glob("**/*_metadata.json"))
    
    if not json_files:
        print(" No files found to index.")
        return

    for file_path in json_files:
        index_single_json_file(str(file_path), embedder)
    
    print(f"Bulk indexing of {len(json_files)} files complete.")
