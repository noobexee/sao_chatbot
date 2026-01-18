from typing import List, Optional
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from src.config import settings
from src.app.llm_base.base import BaseLLM


class GeminiLLM(BaseLLM):
    ALLOWED_MIME = "text/plain"

    def __init__(self, model_name: str | None = None):
        self._llm_instance = ChatGoogleGenerativeAI(
            model=model_name or settings.GEMINI_MODEL,
            google_api_key=settings.GOOGLE_API_KEY,
            temperature=0.7,
        )

    def get_model(self):
        return self._llm_instance

    def invoke(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        txt_files: Optional[List[bytes]] = None,
        mime_types: Optional[List[str]] = None,
    ) -> AIMessage:
        
        """
        Invoke Gemini with prompt + optional system prompt + TXT files only
        """

        messages = []
        if system_prompt:
            messages.append(SystemMessage(content=system_prompt))
        human_content = [prompt]
        if txt_files:
            if not mime_types or len(txt_files) != len(mime_types):
                raise ValueError("txt_files and mime_types must match")
            for file_bytes, mime in zip(txt_files, mime_types):
                self._validate_txt_file(file_bytes, mime)
                text = file_bytes.decode("utf-8")
                human_content.append(
                    "\n\n--- ATTACHED TXT FILE ---\n"
                    + text
                )
        messages.append(HumanMessage(content=human_content))
        return self._llm_instance.invoke(messages)
    def _validate_txt_file(self, file_bytes: bytes, mime: str):
        if mime != self.ALLOWED_MIME:
            raise ValueError("Only .txt files (text/plain) are allowed")

        try:
            file_bytes.decode("utf-8")
        except UnicodeDecodeError:
            raise ValueError("TXT files must be UTF-8 encoded")
        
# Example usage:
'''
with open("law_2567.txt", "rb") as f1, open("amend_2568.txt", "rb") as f2:
    response = llm.invoke(
        system_prompt="Merge documents following legal amendment rules.",
        prompt="Merge these documents.",
        txt_files=[f1.read(), f2.read()],
        mime_types=["text/plain", "text/plain"],
    )
'''