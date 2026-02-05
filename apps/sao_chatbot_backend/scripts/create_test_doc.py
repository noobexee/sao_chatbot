from src.app.chatbot.utils.chunking import chunk_by_clause
from src.app.chatbot.utils.embedding import BGEEmbedder
from src.app.chatbot.utils.preprocess_dataset import index_single_json_file

if __name__ == "__main__":
    file_path = "data/test/test1.txt"
                
    with open(file_path, 'r', encoding='utf-8') as f:
        file = f.read()

    #fill up all field
    chunk = chunk_by_clause(text=file, document_id="test1")
    #chunk = chunk_by_size(text=file, document_id="test1")
    embedder = BGEEmbedder()
    index_single_json_file(chunk, embedder=embedder)