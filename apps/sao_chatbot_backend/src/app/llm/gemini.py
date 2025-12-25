from src.config import settings
from src.app.llm.base import BaseLLM
from langchain.chat_models import init_chat_model

class GeminiLLM(BaseLLM):
    def __init__(self, model_name="gemini-2.5-flash", temperature=0.7):
        self.llm = init_chat_model(
            model_name,
            model_provider="google_genai",
            temperature=temperature,
            google_api_key=settings.GOOGLE_API_KEY
        )

    def invoke(self, prompt: str, **kwargs) -> str:
        return self.llm.invoke(prompt, **kwargs).content
