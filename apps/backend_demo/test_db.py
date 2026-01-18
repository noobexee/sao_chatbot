import os
from repository import AuditRepository
from db import get_db_connection
from dotenv import load_dotenv

# Load Environment Variables
load_dotenv()

def test_connection_and_save():
    print("🔄 Testing Database Connection...")
    
    # 1. Test Connection
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT 1")
        print("✅ Connection Successful!")
        cur.close()
        conn.close()
    except Exception as e:
        print(f"❌ Connection Failed: {e}")
        return

    repo = AuditRepository()
    test_audit_id = "0c4913e6-7aa1-4216-b34a-b4a62b025417"
    test_filename = "test_file_verification.pdf"

    # 2. Test Saving Session
    print(f"\n🔄 Testing save_audit_session (ID: {test_audit_id})...")
    try:
        success = repo.save_audit_session(test_audit_id, test_filename)
        if success:
            print("✅ Session Save Success!")
        else:
            print("❌ Session Save Returned False")
    except Exception as e:
        print(f"❌ Session Save Failed: {e}")
        return

    # 3. Test Saving AI Log (Step 4 Data)
    print("\n🔄 Testing save_step_log (Step 4 Mock Data)...")
    mock_ai_result = {
        "details": {
            "entity": "Test Entity",
            "behavior": "Test Behavior Corruption",
            "official": "Mr. Test Official"
        }
    }
    
    try:
        success = repo.save_step_log(test_audit_id, 4, mock_ai_result)
        if success:
            print("✅ Log Save Success!")
        else:
            print("❌ Log Save Returned False")
    except Exception as e:
        print(f"❌ Log Save Failed: {e}")

    # 4. Verify Data by Fetching
    print("\n🔄 Verifying Data in DB...")
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Check Session
        cur.execute("SELECT * FROM audit_sessions WHERE audit_id = %s", (test_audit_id,))
        session = cur.fetchone()
        if session:
            print(f"   [Found Session]: {session}")
        else:
            print("   [Error] Session not found in DB")

        # Check Logs
        cur.execute("SELECT * FROM audit_feedback_logs WHERE audit_id = %s", (test_audit_id,))
        logs = cur.fetchall()
        print(f"   [Found Logs]: Found {len(logs)} rows")
        for log in logs:
            print(f"    - {log}")

        cur.close()
        conn.close()
        
        print("\n✨ TEST COMPLETE ✨")
        print("You should verify that the data above matches what was inserted.")

    except Exception as e:
        print(f"❌ Verification Failed: {e}")

if __name__ == "__main__":
    test_connection_and_save()