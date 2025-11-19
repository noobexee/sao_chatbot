import os

from src.app.services.gemini_service import GeminiService
from src.app.services.llm_base_service import BaseLLM
from src.app.services.typhoon_service import TyphoonService


def get_llm() -> "BaseLLM":
    """
    Factory to initialize LLM based on environment variable
    """
    llm_choice = os.getenv("LLM_MODEL", "gemini").lower()

    if llm_choice == "gemini":
        return GeminiService()
    elif llm_choice == "typhoon":
        return TyphoonService()
    else:
        raise ValueError(f"Unsupported LLM_MODEL: {llm_choice}")
