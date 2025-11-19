from abc import ABC, abstractmethod
from typing import Any

class BaseLLM(ABC):
    """Abstract Base Class for any LLM"""

    @abstractmethod
    def invoke(self, prompt: str, **kwargs: Any) -> str:
        """Invoke the LLM with a prompt and return the response"""
        pass
