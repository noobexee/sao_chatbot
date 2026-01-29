import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
    TYPHOON_API_KEY = os.getenv("TYPHOON_API_KEY")
    SQL_DATABASE_URL = os.getenv("SQL_DATABASE_URL")
    TYPHOON_API_BASE_URL = os.getenv("TYPHOON_API_BASE_URL", "https://api.opentyphoon.ai/v1")
    TYPHOON_MODEL = os.getenv("TYPHOON_MODEL", "typhoon-v2.1-12b-instruct")
    GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    
settings = Settings()
