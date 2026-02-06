from src.app.utils.chunking import chunk_by_clause
from src.app.utils.embedding import BGEEmbedder
from src.app.utils.preprocess_dataset import index_single_json_file, update_document_expiry_pipeline

if __name__ == "__main__":
    old_document_id = "test1"
    new_document_id = "test2"
    update_document_expiry_pipeline(old_document_id, "2999-01-01")

    file_path = "data/test/test2.txt"
                
    with open(file_path, 'r', encoding='utf-8') as f:
        file = f.read()

    #fill up all field
    #replace file with your .txt file
    chunk = chunk_by_clause(text=file, document_id=new_document_id)
    #chunk = chunk_by_size(text=file, document_id="test1")
    embedder = BGEEmbedder()
    index_single_json_file(chunk, embedder=embedder)