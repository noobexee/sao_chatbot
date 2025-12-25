import os
from src.app.llm.base import BaseLLM
from src.app.llm.gemini import GeminiLLM
from src.app.llm.typhoon import TyphoonLLM

def get_llm() -> "BaseLLM":
    llm_choice = os.getenv("LLM_MODEL", "gemini").lower()

    if llm_choice == "gemini":
        return GeminiLLM()
    elif llm_choice == "typhoon":
        return TyphoonLLM()
    else:
        raise ValueError(f"Unsupported LLM_MODEL: {llm_choice}")
