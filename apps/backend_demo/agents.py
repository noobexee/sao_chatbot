import json
import os
from google import genai
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configure Gemini Client
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    print("WARNING: GEMINI_API_KEY not found in environment variables.")

# Initialize the client
client = genai.Client(api_key=api_key)

class AuditAgents:
    
    def _call_gemini(self, system_prompt, user_text):
        """Helper function to call Gemini with JSON enforcement using the new google.genai SDK"""
        try:
            # Prepare the prompt
            full_prompt = f"{system_prompt}\n\nเอกสารที่ต้องตรวจสอบ:\n{user_text}"

            # Call the model
            # using 'gemini-2.5-flash'
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=full_prompt,
                config={
                    'response_mime_type': 'application/json'
                }
            )
            
            # Parse JSON result
            # The new SDK response object has a .text property just like the old one
            return json.loads(response.text)

        except Exception as e:
            print(f"Gemini Error: {e}")
            return None

    # --- AGENT 1: Sufficiency Check (Step 4) ---
    def agent_step4_sufficiency(self, text):
        system_prompt = """
        คุณคือ 'ผู้ตรวจสอบภายใน' ผู้เชี่ยวชาญระเบียบการตรวจเงินแผ่นดิน
        หน้าที่: วิเคราะห์ข้อความในเอกสารว่ามีรายละเอียดเพียงพอที่จะตรวจสอบต่อหรือไม่
        
        เกณฑ์การผ่าน (Required - ต้องมีครบ):
        1. ชื่อหน่วยรับตรวจ (Entity) เช่น โรงเรียน..., เทศบาล..., อบต...
        2. พฤติการณ์การกระทำ (Behavior) เช่น ทุจริต, นำรถไปใช้ส่วนตัว, เบิกจ่ายเท็จ
        
        ข้อมูลเสริม (Optional - มีหรือไม่มีก็ได้):
        - เจ้าหน้าที่ผู้ถูกร้อง (Official)
        - วันเวลาที่เกิดเหตุ (Date)
        - สถานที่เกิดเหตุ (Location)

        ตอบกลับเป็น JSON เท่านั้นตามรูปแบบนี้:
        {
            "status": "success" หรือ "fail", 
            "title": "ข้อสรุปสั้นๆ (ภาษาไทย)",
            "reason": "เหตุผลประกอบ (ภาษาไทย)",
            "details": {
                "entity": "ชื่อหน่วยงานที่พบ หรือ null",
                "behavior": "พฤติการณ์ที่พบ หรือ null",
                "official": "ชื่อเจ้าหน้าที่ หรือ null",
                "date": "วันเวลา หรือ null",
                "location": "สถานที่ หรือ null"
            }
        }
        """
        return self._call_gemini(system_prompt, text)

    # --- AGENT 2: Complainant Identification (Step 6) ---
    def agent_step6_complainant(self, text):
        system_prompt = """
        คุณคือ 'เจ้าหน้าที่ธุรการ' หน้าที่ของคุณคือแยกแยะบุคคลในเอกสารร้องเรียน
        
        หน้าที่:
        1. ค้นหารายชื่อบุคคลทั้งหมดในเอกสาร (ชื่อ-นามสกุล)
        2. ระบุบทบาทของแต่ละคน โดยดูจากบริบทประโยค
           - "ผู้ร้องเรียน": ผู้ที่ยื่นเรื่อง, แทนตัวเองว่า 'ข้าพเจ้า', 'ผู้ร้อง'
           - "ผู้ถูกร้องเรียน": ผู้ที่ถูกกล่าวหา, ถูกระบุว่ากระทำผิด
           - "พยาน/บุคคลที่เกี่ยวข้อง": บุคคลอื่นๆ ที่ถูกอ้างถึง
        
        ตอบกลับเป็น JSON เท่านั้นตามรูปแบบนี้:
        {
            "people": [
                { "name": "ชื่อ-นามสกุล", "role": "ผู้ร้องเรียน" หรือ "ผู้ถูกร้องเรียน" หรือ "พยาน" }
            ]
        }
        """
        return self._call_gemini(system_prompt, text)

audit_agents = AuditAgents()