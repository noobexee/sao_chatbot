import os
import requests
from typing import Any, List, Dict
from src.app.services.llm_base_service import BaseLLM


class TyphoonService(BaseLLM):
    def __init__(self, model: str | None = None):
        # Use the Typhoon web API base URL (OpenTyphoon API)
        # According to docs, it supports OpenAI-compatible API at /v1/chat/completions :contentReference[oaicite:1]{index=1}
        self.base_url = os.getenv("TYPHOON_API_BASE_URL", "https://api.opentyphoon.ai/v1")
        self.api_key = os.getenv("TYPHOON_API_KEY", "")
        self.model = model or os.getenv("TYPHOON_MODEL", "typhoon-v2.1-12b-instruct")

    def invoke(self, prompt: str, **kwargs: Any) -> str:
        """
        Call the Typhoon API (OpenAI-compatible) to get a chat completion.
        Returns only the content string.
        """

        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        messages: List[Dict[str, str]] = [
            {"role": "user", "content": prompt}
        ]

        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
          
        }

        if "temperature" in kwargs:
            payload["temperature"] = kwargs["temperature"]
        if "max_tokens" in kwargs:
            payload["max_tokens"] = kwargs["max_tokens"]
        if "top_p" in kwargs:
            payload["top_p"] = kwargs["top_p"]
        if "n" in kwargs:
            payload["n"] = kwargs["n"]

        response = requests.post(url, json=payload, headers=headers, timeout=30)
        try:
            response.raise_for_status()
        except requests.RequestException as e:
            raise RuntimeError(f"Typhoon API call failed: {e} - {response.text}")

        data = response.json()
        choices = data.get("choices")
        if not choices or len(choices) == 0:
            raise RuntimeError(f"Typhoon API returned no choices: {data}")

        content = choices[0].get("message", {}).get("content", "")
        return content
