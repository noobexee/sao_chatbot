import psycopg2
from db import get_db_connection

def fix_database_constraint():
    print("🔧 Starting Database Fix (Boolean Version)...")
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # 1. Drop problematic constraint
        print("   - Dropping problematic constraint 'audit_feedback_logs_result_correct_check'...")
        cur.execute("""
            ALTER TABLE audit_feedback_logs 
            DROP CONSTRAINT IF EXISTS audit_feedback_logs_result_correct_check;
        """)

        # 2. Change column type to BOOLEAN
        # The 'USING' clause handles conversion: 1 -> true, 0 -> false
        print("   - Altering 'result_correct' column to BOOLEAN...")
        cur.execute("""
            ALTER TABLE audit_feedback_logs 
            ALTER COLUMN result_correct TYPE BOOLEAN 
            USING (CASE WHEN result_correct::text = '1' THEN true ELSE false END);
        """)
        
        # NOTE: You generally don't need a CHECK constraint for a BOOLEAN column 
        # because the type itself enforces true/false/null.

        conn.commit()
        cur.close()
        print("✅ Database Fixed Successfully! Column is now BOOLEAN.")

    except Exception as e:
        print(f"❌ Error Fixing DB: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    fix_database_constraint()