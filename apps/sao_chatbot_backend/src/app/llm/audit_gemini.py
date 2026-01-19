import os
from langchain_google_genai import ChatGoogleGenerativeAI
from src.config import settings

class Audit_GeminiLLM:
    def __init__(self, api_key: str):
        if not api_key:
            print("⚠️ Warning: GOOGLE_API_KEY is missing in settings.")

        os.environ["GOOGLE_API_KEY"] = api_key 
        self.api_key = api_key

    def invoke(self, model: str, contents: str, config: dict = None):
        """
        Wrapper function to call Gemini API via LangChain
        """
        try:
            # ✅ Fix: Prepare model_kwargs to pass config (like response_mime_type)
            model_kwargs = {}
            if config:
                if 'response_mime_type' in config:
                    model_kwargs['response_mime_type'] = config['response_mime_type']
                # Add other config keys if necessary (e.g. top_k, top_p)

            llm = ChatGoogleGenerativeAI(
                model=model,
                google_api_key=self.api_key,
                temperature=0, # Example default
                model_kwargs=model_kwargs # ✅ Pass the config here
            )
            response = llm.invoke(contents)

            class ResponseWrapper:
                def __init__(self, content):
                    self.text = content
            
            return ResponseWrapper(response.content)
            
        except Exception as e:
            print(f"❌ Gemini Invoke Error: {e}")
            raise e