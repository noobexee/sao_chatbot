import os
from langchain_openai import ChatOpenAI
from src.config import settings
from src.app.llm.base import BaseLLM

class TyphoonLLM(BaseLLM):
    def __init__(self, model_name: str | None = None):  
        self._llm_instance = ChatOpenAI(
            base_url=settings.TYPHOON_API_BASE_URL,
            api_key=settings.TYPHOON_API_KEY,
            model=model_name or settings.TYPHOON_MODEL,
            temperature=0.7,
            max_tokens=8192
        )

    def get_model(self):
        return self._llm_instance