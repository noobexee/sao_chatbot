from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.config import settings

DATABASE_URL = settings.SQL_DATABASE_URL

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
