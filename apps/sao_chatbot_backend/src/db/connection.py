import os
import psycopg2
from psycopg2.extensions import connection

def get_db_connection() -> connection:

    db_url = os.getenv("SQL_DATABASE_URL")
    
    if not db_url:
        raise ValueError("SQL_DATABASE_URL is not set in environment variables.")
    
    try:
        conn = psycopg2.connect(db_url)
        return conn
    except Exception as e:
        print(f"Database Connection Failed: {e}")
        raise e