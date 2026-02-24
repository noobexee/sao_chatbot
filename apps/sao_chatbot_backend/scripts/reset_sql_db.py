import sys
import os
from dotenv import load_dotenv

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.db.connection import get_db_connection

def drop_all_tables():
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        print("STARTING DATABASE RESET...")

        cur.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
        """)
        tables = cur.fetchall()

        if not tables:
            print("No tables found. Database is already empty.")
            return

        for table in tables:
            table_name = table[0]
            print(f"Dropping table: {table_name}...")
            cur.execute(f'DROP TABLE IF EXISTS "{table_name}" CASCADE')

        conn.commit()
        print("SUCCESS: All tables have been deleted.")

    except Exception as e:
        print(f"ERROR: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    load_dotenv()
    confirmation = input("Type 'DELETE' to confirm you want to wipe the database: ")
    if confirmation == "DELETE":
        drop_all_tables()
    else:
        print("Operation cancelled.")