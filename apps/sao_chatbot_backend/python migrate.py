import sqlite3
import os
import importlib.util

# Configuration
DB_NAME = "my_app.db"
MIGRATIONS_DIR = "migrations"

def run_migrations():
    print(f"--- Checking Database: {DB_NAME} ---")

    # 1. Check if migrations folder exists
    if not os.path.exists(MIGRATIONS_DIR):
        print(f"❌ Error: Directory '{MIGRATIONS_DIR}' not found.")
        print("   Please create a folder named 'migrations' and put your 001_... files inside.")
        return

    # 2. Get all python files and sort them numerically
    # Sorting ensures 001 runs before 002
    files = sorted([f for f in os.listdir(MIGRATIONS_DIR) if f.endswith(".py")])

    if not files:
        print("⚠️  No migration files found in the folder.")
        return

    print(f"📂 Found {len(files)} migration files. Starting execution...\n")

    # 3. Loop through and execute each file
    for filename in files:
        print(f"▶️  Running: {filename}...")
        
        # Path to the specific migration file
        filepath = os.path.join(MIGRATIONS_DIR, filename)
        
        # Dynamic Import Logic (Standard Python mechanism to load a file as code)
        spec = importlib.util.spec_from_file_location("migration_module", filepath)
        module = importlib.util.module_from_spec(spec)
        
        try:
            # Load the module
            spec.loader.exec_module(module)
            
            # Execute the 'run' function inside the migration file
            if hasattr(module, 'run'):
                module.run()
                print(f"✅ Success: {filename}\n")
            else:
                print(f"⚠️  Warning: {filename} has no 'run()' function. Skipped.\n")
                
        except Exception as e:
            print(f"❌ FAILED: {filename}")
            print(f"   Error details: {e}")
            print("⛔ Stopping migrations due to error.")
            break

    print("--- Migration Process Finished ---")

if __name__ == "__main__":
    run_migrations()