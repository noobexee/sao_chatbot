from src.app.utils.chunking import chunk_by_clause
from src.app.utils.embedding import BGEEmbedder
from src.app.utils.preprocess_dataset import update_document_pipeline

if __name__ == "__main__":
    file_path = "data/test/test1.txt"
                
    with open(file_path, 'r', encoding='utf-8') as f:
        file = f.read()

    chunks = chunk_by_clause(text=file, document_id="test1", expire_date="2999-01-01")
    #chunk = chunk_by_size(text=file, document_id="test1")
    embedder = BGEEmbedder()
    update_document_pipeline("test1", chunks, embedder=embedder)