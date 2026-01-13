import os
from langchain_openai import ChatOpenAI

from src.app.llm.base import BaseLLM

class TyphoonLLM(BaseLLM):
    def __init__(self, model_name: str | None = None):  
        self._llm_instance = ChatOpenAI(
            base_url=os.getenv("TYPHOON_API_BASE_URL", "https://api.opentyphoon.ai/v1"),
            api_key=os.getenv("TYPHOON_API_KEY", ""),
            model=model_name or os.getenv("TYPHOON_MODEL", "typhoon-v2.1-12b-instruct"),
            temperature=0.7,
            max_tokens=4096
        )

    def get_model(self):
        return self._llm_instance