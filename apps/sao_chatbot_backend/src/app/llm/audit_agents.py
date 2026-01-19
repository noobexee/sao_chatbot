import json

from sympy import re
from src.config import settings
from src.app.llm.audit_gemini import Audit_GeminiLLM

api_key = settings.GOOGLE_API_KEY
client = Audit_GeminiLLM(api_key=api_key)

class AuditAgents:
    
    def _call_gemini(self, system_prompt, user_text):
        try:
            full_prompt = f"{system_prompt}\n\nเอกสารที่ต้องตรวจสอบ:\n{user_text}"
            response = client.invoke(
                model='gemini-2.5-flash',
                contents=full_prompt,
                config={
                    'response_mime_type': 'application/json'
                }
            )
            content = response.text
            if not content:
                print("⚠️ Gemini returned empty content.")
                return None

            # ✅ Fix: Clean Markdown code blocks (```json ... ```) if present
            if "```" in content:
                content = re.sub(r"^```json\s*", "", content, flags=re.MULTILINE)
                content = re.sub(r"^```\s*", "", content, flags=re.MULTILINE)
                content = re.sub(r"```$", "", content, flags=re.MULTILINE)
            
            return json.loads(content.strip())

        except Exception as e:
            print(f"Gemini Error: {e}")
            if 'response' in locals():
                print(f"Raw Response: {response.text}") # Debug log
            return None

    # --- AGENT 1: Step 4 (Detailed Sufficiency Check) ---
    def agent_step4_sufficiency(self, text):
        system_prompt = """
        คุณคือ 'ผู้เชี่ยวชาญด้านการตรวจสอบเรื่องร้องเรียนของ สตง.' หน้าที่คือวิเคราะห์องค์ประกอบของเรื่องร้องเรียน
        
        **คำสั่งสำคัญ:** - ต้องดึงข้อมูลออกมาเป็น **Object เดียวเท่านั้น** (ห้ามตอบเป็น List หรือ Array ใน field 'details')
        - หากพบหลายเหตุการณ์ ให้สรุปรวมเป็นข้อความเดียวในแต่ละ field
        
        ให้ดึงข้อมูลดังต่อไปนี้ออกมา (ถ้าไม่พบให้ใส่ null):
        1. **ชื่อหน่วยรับตรวจ (Entity):** ต้องเป็นชื่อหน่วยงานที่ชัดเจน (เช่น "เทศบาลตำบล ก.", "โรงเรียนวัด...", "กรมทางหลวง") 
           - *ห้าม* ตอบคำลอยๆ เช่น "เทศบาลแห่งหนึ่ง", "หน่วยงานราชการ", "อบต." ถ้าไม่ระบุชื่อเฉพาะให้ถือว่า null
        2. **พฤติการณ์ (Behavior):** การกระทำที่ถูกกล่าวหา (เช่น "ทุจริตจัดซื้อ", "นำรถหลวงไปใช้ส่วนตัว")
        3. **เจ้าหน้าที่ผู้ถูกร้อง (Official):** ชื่อ-นามสกุล หรือตำแหน่งที่ระบุตัวตนได้ชัดเจน ของผู้ที่ถูกกล่าวหา
            - *ต้องเป็นชื่อเฉพาะบุคคลเท่านั้น* ต้องมีคำนำหน้า (นาย, นาง, นางสาว, ยศ) ตามด้วยชื่อและนามสกุลจริง
            - *ห้าม* นับนามแฝงหรือชื่อสมมติ เช่น "พลเมืองดี", "ผู้หวังดี", "ชาวบ้าน", "ข้าราชการชั้นผู้น้อย" เป็นชื่อคนเด็ดขาด
            - *ห้าม* นับนามแฝงหรือชื่อสมมติ เช่น "พลเมืองดี", "ผู้หวังดี", "ชาวบ้าน", "ข้าราชการชั้นผู้น้อย" เป็นชื่อคนเด็ดขาด
        4. **วันเวลา (Date):** ช่วงเวลาที่เกิดเหตุ
        5. **สถานที่ (Location):** สถานที่เกิดเหตุ (จังหวัด, อำเภอ หรือสถานที่เกิดเหตุ)
        
        **เกณฑ์การตัดสิน (Status):**
        - "success": ถ้าพบ (Entity และ Behavior และ Official) ครบถ้วน
        - "fail": ถ้าขาด Entity หรือ Behavior หรือ Officialอย่างใดอย่างหนึ่ง

        ตอบกลับเป็น JSON Structure นี้เท่านั้น:
        {
            "status": "success" หรือ "fail", 
            "title": "ข้อสรุปสั้นๆ (ภาษาไทย)",
            "reason": "เหตุผลประกอบ (ระบุว่าพบหรือขาดอะไร)",
            "details": {
                "entity": "ชื่อหน่วยงานเฉพาะเจาะจง หรือ null",
                "behavior": "พฤติการณ์ หรือ null",
                "official": "ชื่อ/ตำแหน่งผู้ถูกร้อง หรือ null",
                "date": "วันเวลา หรือ null",
                "location": "สถานที่ หรือ null"
            }
        }
        """
        return self._call_gemini(system_prompt, text)

    # --- AGENT 2: Step 6 (Specific Person Check) ---
    def agent_step6_complainant(self, text):
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