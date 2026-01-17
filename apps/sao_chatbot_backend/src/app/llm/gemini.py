import os
from langchain_google_genai import ChatGoogleGenerativeAI
from src.config import settings
from src.app.llm.base import BaseLLM

class GeminiLLM(BaseLLM):
    def __init__(self, model_name: str | None = None):
        # Using the direct class constructor to match ChatOpenAI pattern
        self._llm_instance = ChatGoogleGenerativeAI(
            model=model_name or settings.GEMINI_MODEL,
            google_api_key=settings.GOOGLE_API_KEY, 
            temperature=0.7
        )

    def get_model(self):
        return self._llm_instance