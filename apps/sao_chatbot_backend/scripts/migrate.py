import os
import psycopg2

from dotenv import load_dotenv

load_dotenv()

def run_migrations():
    db_url = os.getenv("SQL_DATABASE_URL")
    if not db_url:
        print("Error: SQL_DATABASE_URL is missing from .env")
        return

    current_script_dir = os.path.dirname(os.path.abspath(__file__))
    migrations_dir = os.path.join(current_script_dir, '../db/migrations')

    if not os.path.exists(migrations_dir):
        print(f"Error: Migrations directory not found at: {migrations_dir}")
        return

    conn = None
    try:
        conn = psycopg2.connect(db_url)
        conn.autocommit = True
        cur = conn.cursor()
        
        print("🔌 Connected to PostgreSQL")
        print(f"📂 Scanning for SQL files in: {migrations_dir}")


        files = sorted([f for f in os.listdir(migrations_dir) if f.endswith('.sql')])
        
        if not files:
            print("⚠️  No SQL files found in migrations directory.")
            return

        print(f"📝 Found {len(files)} migration files.")

        for filename in files:
            file_path = os.path.join(migrations_dir, filename)
            print(f"🚀 Running {filename}...")
            
            with open(file_path, 'r', encoding='utf-8') as f:
                sql_commands = f.read()
                
                try:
                    cur.execute(sql_commands)
                    print(f"Success")
                except Exception as e:
                    print(f"Failed to run {filename}")
                    print(f"ERROR: {e}")
                    return 

        print("\n✨ All migrations executed successfully!")

    except psycopg2.OperationalError as e:
        print(f"Connection Error: Could not connect to database.")
        print(f"Details: {e}")
    except Exception as e:
        print(f"Unexpected Error: {e}")
    finally:
        if conn:
            cur.close()
            conn.close()
            print("🔌 Connection closed.")

if __name__ == "__main__":
    run_migrations()