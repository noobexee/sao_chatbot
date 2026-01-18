import json
from src.config import settings
from src.app.llm.gemini import GeminiLLM

# --- MOCK MODE CONFIGURATION ---
USE_MOCK_AI = False  # Set to True to save API quota, False to use real Gemini

api_key = settings.GEMINI_API_KEY
if not USE_MOCK_AI and not api_key:
    print("WARNING: GEMINI_API_KEY not found.")

if not USE_MOCK_AI:
    client = GeminiLLM
else:
    client = None
    print("⚠️ RUNNING IN MOCK AI MODE")

class AuditAgents:
    
    def _call_gemini(self, system_prompt, user_text):
        if USE_MOCK_AI:
            return None 

        try:
            full_prompt = f"{system_prompt}\n\nเอกสารที่ต้องตรวจสอบ:\n{user_text}"
            response = client.invoke(
                model='gemini-2.5-flash',
                contents=full_prompt,
                config={
                    'response_mime_type': 'application/json'
                }
            )
            return json.loads(response.text)
        except Exception as e:
            print(f"Gemini Error: {e}")
            return None

    # --- AGENT 1: Step 4 (Detailed Sufficiency Check) ---
    def agent_step4_sufficiency(self, text):
        if USE_MOCK_AI:
            print("   [Mock AI] Returning Step 4 Mock Data (Single Object)")
            return {
                "status": "success",
                "title": "รายละเอียดครบถ้วน (Mock)",
                "reason": "พบองค์ประกอบครบ (Mock)",
                "details": {
                    "entity": "เทศบาลตำบลหนองปรือ (Mock)",
                    "behavior": "ทุจริตการจัดซื้อ (Mock)",
                    "official": "นายสมชาย (Mock)",
                    "date": "2567 (Mock)",
                    "location": "ชลบุรี (Mock)"
                }
            }

        # --- IMPROVED PROMPT TO PREVENT LIST OUTPUT ---
        system_prompt = """
        คุณคือ 'ผู้เชี่ยวชาญด้านการตรวจสอบเรื่องร้องเรียนของ สตง.' หน้าที่คือวิเคราะห์องค์ประกอบของเรื่องร้องเรียน
        
        **คำสั่งสำคัญ:** - ต้องดึงข้อมูลออกมาเป็น **Object เดียวเท่านั้น** (ห้ามตอบเป็น List หรือ Array ใน field 'details')
        - หากพบหลายเหตุการณ์ ให้สรุปรวมเป็นข้อความเดียวในแต่ละ field
        
        ให้ดึงข้อมูลดังต่อไปนี้ออกมา (ถ้าไม่พบให้ใส่ null):
        1. **ชื่อหน่วยรับตรวจ (Entity):** ชื่อหน่วยงานที่ชัดเจน
        2. **พฤติการณ์ (Behavior):** การกระทำที่ถูกกล่าวหา
        3. **เจ้าหน้าที่ผู้ถูกร้อง (Official):** ชื่อ-นามสกุล หรือตำแหน่ง
        4. **วันเวลา (Date):** ช่วงเวลาที่เกิดเหตุ
        5. **สถานที่ (Location):** สถานที่เกิดเหตุ
        
        ตอบกลับเป็น JSON Structure นี้เท่านั้น:
        {
            "status": "success" หรือ "fail", 
            "title": "ข้อสรุปสั้นๆ",
            "reason": "เหตุผลประกอบ",
            "details": {
                "entity": "...",
                "behavior": "...",
                "official": "...",
                "date": "...",
                "location": "..."
            }
        }
        """
        return self._call_gemini(system_prompt, text)

    # --- AGENT 2: Step 6 (Specific Person Check) ---
    def agent_step6_complainant(self, text):
        if USE_MOCK_AI:
            print("   [Mock AI] Returning Step 6 Mock Data")
            return {
                "status": "success",
                "title": "รายละเอียดบุคคล (Mock)",
                "people": [
                    { "name": "นาย ก. (Mock)", "role": "ผู้ร้องเรียน" },
                    { "name": "นาย ข. (Mock)", "role": "ผู้ถูกร้องเรียน" }
                ]
            }

        system_prompt = """
        คุณคือ 'นายทะเบียน' หน้าที่คือตรวจสอบรายชื่อบุคคลในเอกสาร
        
        ตอบกลับเป็น JSON เท่านั้น:
        {
            "people": [
                { "name": "ชื่อ-นามสกุลจริงเท่านั้น", "role": "ผู้ร้องเรียน" หรือ "ผู้ถูกร้องเรียน" หรือ "พยาน" }
            ]
        }
        """
        return self._call_gemini(system_prompt, text)

    # --- AGENT 3: Step 2 (Jurisdiction Check - NEW!) ---
    def agent_step2_jurisdiction(self, text):
        pass

audit_agents = AuditAgents()