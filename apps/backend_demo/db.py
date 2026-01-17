import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

def get_db_connection():
    """
    Establishes a connection to the PostgreSQL database using psycopg2.
    """
    # Try getting from ENV first, fallback to default if missing
    db_url = os.getenv("SQL_DATABASE_URL", "postgresql://user:supersecretpassword@localhost:5432/mydatabase")
    
    if not db_url:
        raise ValueError("SQL_DATABASE_URL is not set in environment variables.")
    
    try:
        conn = psycopg2.connect(db_url)
        return conn
    except Exception as e:
        print(f"❌ Database Connection Failed: {e}")
        raise e