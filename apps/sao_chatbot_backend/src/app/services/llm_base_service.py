from abc import ABC, abstractmethod
from typing import Any

class BaseLLM(ABC):

    @abstractmethod
    def get_model(self) -> Any:
        pass