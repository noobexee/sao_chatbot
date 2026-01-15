import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
    TYPHOON_API_KEY = os.getenv("TYPHOON_API_KEY")
    SQL_DATABASE_URL = os.getenv("SQL_DATABASE_URL")
    
settings = Settings()
