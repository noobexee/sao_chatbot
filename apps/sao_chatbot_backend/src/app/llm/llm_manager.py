from src.app.llm.typhoon import TyphoonLLM
from src.app.llm.qwen import QwenLLM
from src.config import settings

_instances = {}

def get_llm(provider: str | None = None):
    provider = provider or settings.DEFAULT_LLM
    provider = provider.lower()

    if provider in _instances:
        return _instances[provider]
    if provider == "typhoon":
        instance = TyphoonLLM()
    elif provider == "qwen":
        instance = QwenLLM()
    else:
        raise ValueError(f"Unsupported provider: {provider}")

    _instances[provider] = instance
    return instance