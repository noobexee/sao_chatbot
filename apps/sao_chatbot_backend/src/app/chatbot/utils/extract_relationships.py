import json
import os
import glob
import re
import asyncio
from typing import List, Dict

DIRECTORIES = {
    "GUIDELINE": "metadata/แนวทาง",
    "ORDER": "metadata/คำสั่ง"
}
OUTPUT_MASTER = "storage/master_map.json"
OUTPUT_CHECK = "storage/source_check.json"

DEFAULT_REGULATION = "ระเบียบสำนักงานการตรวจเงินแผ่นดินว่าด้วยการตรวจสอบการปฏิบัติตามกฎหมาย"

from src.app.llm.typhoon import TyphoonLLM 

def thai_to_arabic(text: str) -> str:
    if not isinstance(text, str): return text
    return text.translate(str.maketrans("๐๑๒๓๔๕๖๗๘๙", "0123456789"))

def normalize_law_name(text: str) -> str:
    if not text: return ""
    text = thai_to_arabic(text)
    
    # Handle Defaults
    if text.strip() in ["", "ระเบียบ", "ระเบียบฯ", "กฎหมาย", "ระเบียบสำนักงานการตรวจเงินแผ่นดิน"]:
        return normalize_law_name(DEFAULT_REGULATION)

    text = text.replace("สตง.", "สำนักงานการตรวจเงินแผ่นดิน")
    text = re.sub(r'\(ฉบับที่\s*\d+\)', '', text)
    text = re.sub(r'พ\.ศ\.\s*\d+', '', text)
    text = re.sub(r'\s+', '', text).strip()
    return text

def expand_clauses(clause_list: List[str]) -> List[str]:
    """Splits 'ข้อ 36 (2) (3)' into ['ข้อ 36 (2)', 'ข้อ 36 (3)']"""
    expanded = []
    for raw_clause in clause_list:
        c = thai_to_arabic(raw_clause).strip()
        c = re.sub(r'วรรค.*', '', c).strip() # Remove paragraphs

        # Regex: Capture "ข้อ 36" (Group 1) and "(2) (3)" (Group 2)
        match = re.match(r'^(ข้อ\s*\d+)\s*((?:\(\d+\)\s*)+)$', c)
        
        if match:
            base = match.group(1).strip()
            sub_groups = re.findall(r'\(\d+\)', match.group(2))
            for sub in sub_groups:
                expanded.append(f"{base} {sub}")
        else:
            expanded.append(c)
    return expanded


GUIDELINE_PROMPT = """
You are a Legal Data Extractor. Link the Guideline to the Regulation Clause.

[CRITICAL RULE - HANDLING BRACKETS]:
1. **Direct Citation (KEEP BRACKETS):** - If the text says "Clause 36 (2)", extract "Clause 36 (2)".
   - The bracket must **immediately** follow the number (ignoring small spaces).

2. **List Item (IGNORE BRACKETS):**
   - If the text says "Clause 18 ... text ... (1) ... (2)", extract ONLY "Clause 18".
   - If the bracket is separated by text, it is a list item, NOT a sub-clause.

3. **General Rules:**
   - Default Regulation: "{default_reg_name}"
   - Ignore "Acts" (พระราชบัญญัติ).
   - Ignore Paragraphs (วรรค).

[EXAMPLES]:
- Text: "ตามข้อ 36 (2) (3)" -> Output: ["ข้อ 36 (2)", "ข้อ 36 (3)"] (Immediate follow)
- Text: "ข้อ 18 กำหนดหลักเกณฑ์... (1) ... (2)" -> Output: ["ข้อ 18"] (Separated by text)
- Text: "ข้อ 5 วรรคหนึ่ง" -> Output: ["ข้อ 5"]

[INPUT]:
Title: "{title}"
Text: "{text}"

[OUTPUT JSON]:
{{
  "found": true,
  "regulation": "...",
  "clauses": ["..."]
}}
"""

ORDER_PROMPT = """
You are a Legal Syntax Parser. Your ONLY job is to extract clauses that are explicitly cited as the legal basis.

[STRICT FILTERING RULES]:
1. **THE "ATTACHMENT" RULE (CRITICAL)**: 
   - You may ONLY extract a Clause (ข้อ) if it is grammatically ATTACHED to the full regulation name: "ระเบียบสำนักงานการตรวจเงินแผ่นดินว่าด้วยการตรวจสอบการปฏิบัติตามกฎหมาย".
   - **Valid Pattern:** "...อาศัยอำนาจตาม **ข้อ 6 ของระเบียบสำนักงานการตรวจเงินแผ่นดิน...**" -> EXTRACT "ข้อ 6".
   - **Valid Pattern:** "...และ **ข้อ 6 ข้อ 7 ประกอบข้อ 41 ของระเบียบ...**" -> EXTRACT "ข้อ 6, 7, 41".
   - **Invalid Pattern:** "1. ให้สำนัก..." (This is a list item, not a citation) -> IGNORE.
   - **Invalid Pattern:** "...อาศัยอำนาจตาม พ.ร.บ.... มาตรา 5" (Citing Act, not Regulation) -> IGNORE.

2. **IGNORE ORPHANED NUMBERS**:
   - If you see "ข้อ 1" or "1." but it is NOT in the same sentence/phrase as "ของระเบียบ..." (of the Regulation), IT IS FALSE.
   - Do not infer relationships across paragraphs.

3. **DEFAULT NAME**:
   - Use "{default_reg_name}" as the key in output, but ONLY if the text explicitly mentions it.

[LEVEL OF DETAIL RULE]:
- Only extract down to the numeric sub-clause level, e.g., "ข้อ 26 (1)".
- **DO NOT** include Thai alphabetical sub-items like (ก), (ข), (ค). 
- If the text says "ข้อ 26 (1) (ก)", you must output only "ข้อ 26 (1)".

[EXAMPLES]:
- Text: "ตามข้อ 26 (1) (ก)" -> Output: ["ข้อ 26 (1)"]
- Text: "ข้อ 5 (2) (ข)" -> Output: ["ข้อ 5 (2)"]

[TEST CASE - ORDER 22/2566]:
- Text: "...ผู้ว่าการฯ อาศัยอำนาจตาม พ.ร.บ. ... มาตรา 5 ... ออกคำสั่งดังนี้ 1. ให้สำนัก..."
- Analysis: The authority comes from the ACT (Act Section 5). The number "1." is just a list item.
- Result: "found": false

[INPUT]:
Title: "{title}"
Text: "{text}"

[OUTPUT JSON]:
{{
  "found": true/false,
  "regulation": "...",
  "clauses": ["..."]
}}
"""

class RelationshipBuilder:
    def __init__(self):
        self.llm = TyphoonLLM().get_model()
        
        # Structure 1: Regulation -> Clause -> [Files]
        self.master_map = {}
        
        # Structure 2: File -> [Regulation : Clause]
        self.check_map = {}

    def load_context(self, file_path: str) -> Dict:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                chunks = json.load(f)
            chunks = sorted(chunks, key=lambda x: x.get('metadata', {}).get('chunk_index', 0))
            if not chunks: return None
            
            title = chunks[0].get("law_name", "Unknown")
            text = "\n".join([c.get("text", "") for c in chunks[:2]])
            return {"title": title, "text": text}
        except Exception:
            return None

    def update_maps(self, extraction: Dict, source_title: str):
        """
        Updates the Master Map and Check Map with valid extractions.
        """
        if not extraction.get('found'):
            return

        # Normalize Regulation Name
        raw_reg = extraction.get('regulation')
        if not raw_reg or "ระเบียบ" in raw_reg: 
            reg_key = normalize_law_name(DEFAULT_REGULATION)
        else:
            reg_key = normalize_law_name(raw_reg)

        if "พระราชบัญญัติ" in reg_key: 
            return

        source_title_clean = thai_to_arabic(source_title).strip()
        raw_clauses = extraction.get('clauses', [])
        
        # Expand "Clause 36 (2) (3)" -> ["Clause 36 (2)", "Clause 36 (3)"]
        final_clauses = expand_clauses(raw_clauses)

        valid_clauses = []
        
        #SAFETY FILTER for Orders
        is_order = "คำสั่ง" in source_title
        
        for clause in final_clauses:
            # Normalize "ข้อ  6" -> "ข้อ 6"
            c_clean = re.sub(r'\s+', ' ', clause).strip()
            
            if is_order:
                if c_clean in ["ข้อ 1", "ข้อ 2", "ข้อ 3"] and len(final_clauses) > 3:
                    continue 

            valid_clauses.append(c_clean)

        for clause_key in valid_clauses:
            # Master Map: Reg -> Clause -> [Files]
            if clause_key not in self.master_map.setdefault(reg_key, {}):
                self.master_map[reg_key][clause_key] = []
            
            if source_title_clean not in self.master_map[reg_key][clause_key]:
                self.master_map[reg_key][clause_key].append(source_title_clean)

            # Check Map: File -> [Reg : Clause]
            if source_title_clean not in self.check_map:
                self.check_map[source_title_clean] = []
            
            check_entry = f"{reg_key} : {clause_key}"
            if check_entry not in self.check_map[source_title_clean]:
                self.check_map[source_title_clean].append(check_entry)
                
    async def run(self):
        print("Starting Extraction...")

        # Process Both Directories
        for doc_type, dir_path in DIRECTORIES.items():
            if not os.path.exists(dir_path): continue
            
            files = glob.glob(os.path.join(dir_path, "*.json"))
            for f_path in files:
                data = self.load_context(f_path)
                if not data or "พระราชบัญญัติ" in data['title']: continue
                if "ยกเลิกคำสั่ง" in data['text'][:200]: continue

                try:
                    if doc_type == "GUIDELINE" :
                        prompt = GUIDELINE_PROMPT.format(
                            title=data['title'], 
                            text=data['text'][:3500],
                            default_reg_name=DEFAULT_REGULATION
                        )
                    else :
                        prompt = ORDER_PROMPT.format(
                            title=data['title'], 
                            text=data['text'][:3500],
                            default_reg_name=DEFAULT_REGULATION
                        )
                    
                    resp = await self.llm.ainvoke(prompt)
                    clean_content = resp.content.strip().replace("```json", "").replace("```", "")
                    
                    if "found" not in clean_content: continue
                    result = json.loads(clean_content)

                    if result.get("found"):
                        self.update_maps(result, data['title'])
                        print(f"  ✅ Processed: {data['title'][:40]}")

                except Exception as e:
                    print(f"Error: {e}")

        # --- SAVE FILE 1: MASTER MAP ---
        os.makedirs(os.path.dirname(OUTPUT_MASTER), exist_ok=True)
        with open(OUTPUT_MASTER, 'w', encoding='utf-8') as f:
            json.dump(self.master_map, f, ensure_ascii=False, indent=4)
        print(f"\n💾 Saved Master Map: {OUTPUT_MASTER}")

        # --- SAVE FILE 2: CHECK MAP (INVERTED) ---
        with open(OUTPUT_CHECK, 'w', encoding='utf-8') as f:
            json.dump(self.check_map, f, ensure_ascii=False, indent=4)
        print(f"💾 Saved Check Map: {OUTPUT_CHECK}")

if __name__ == "__main__":
    builder = RelationshipBuilder()
    asyncio.run(builder.run())