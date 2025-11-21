from langchain_openai import OpenAIEmbeddings

from src.config import settings


class EmbeddingService:
    def __init__(self):
        self.model = OpenAIEmbeddings(openai_api_key=settings.OPENAI_API_KEY)

    def embed(self, text: str):
        return self.model.embed_query(text)
