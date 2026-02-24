import glob
import json
import os
import re
import asyncio
from typing import List, Dict, Optional, Any

# Assume TyphoonLLM is importable in your actual environment
from src.app.llm.typhoon import TyphoonLLM 

DEFAULT_REGULATION = "ระเบียบสำนักงานการตรวจเงินแผ่นดินว่าด้วยการตรวจสอบการปฏิบัติตามกฎหมาย"

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

def thai_to_arabic(text: str) -> str:
    if not isinstance(text, str): return text
    return text.translate(str.maketrans("๐๑๒๓๔๕๖๗๘๙", "0123456789"))

def normalize_law_name(text: str) -> str:
    if not text: return ""
    text = thai_to_arabic(text)
    if text.strip() in ["", "ระเบียบ", "ระเบียบฯ", "กฎหมาย", "ระเบียบสำนักงานการตรวจเงินแผ่นดิน"]:
        return normalize_law_name(DEFAULT_REGULATION)
    text = text.replace("สตง.", "สำนักงานการตรวจเงินแผ่นดิน")
    text = re.sub(r'\(ฉบับที่\s*\d+\)', '', text)
    text = re.sub(r'พ\.ศ\.\s*\d+', '', text)
    return re.sub(r'\s+', '', text).strip()

def expand_clauses(clause_list: List[str]) -> List[str]:
    expanded = []
    for raw_clause in clause_list:
        c = thai_to_arabic(raw_clause).strip()
        c = re.sub(r'วรรค.*', '', c).strip()
        match = re.match(r'^(ข้อ\s*\d+)\s*((?:\(\d+\)\s*)+)$', c)
        if match:
            base = match.group(1).strip()
            sub_groups = re.findall(r'\(\d+\)', match.group(2))
            for sub in sub_groups:
                expanded.append(f"{base} {sub}")
        else:
            expanded.append(c)
    return expanded

class LegalReferenceExtractor:
    def __init__(self):
        self.llm = TyphoonLLM().get_model()
        # Internal State (Accumulator)
        self.new_master_map: Dict[str, Dict[str, List[str]]] = {}
        self.new_check_map: Dict[str, List[str]] = {}

    # --- INPUT HANDLER (No files, just Data) ---

    async def process_record(self, record: Dict[str, Any], doc_type: str) -> bool:
        # 1. Extract Title
        title = record.get("law_name", "Unknown Title")
        
        # 2. Extract and Normalize Text (The Fix)
        raw_text = record.get("text", "")
        
        if isinstance(raw_text, list):
            # Handle list of strings OR list of dicts (common in RAG)
            joined_text = ""
            for chunk in raw_text:
                if isinstance(chunk, str):
                    joined_text += chunk + "\n"
                elif isinstance(chunk, dict):
                    joined_text += chunk.get("text", "") + "\n"
            
            # Slice by CHARACTERS, not chunks
            text = joined_text[:4000] 
        else:
            text = str(raw_text)[:4000]

        # Debugging: Uncomment this to see exactly what the LLM sees
        # print(f"--- SENDING TO LLM ({len(text)} chars) ---\n{text[:200]}...\n----------------")

        # 3. Validate / Skip
        if self._should_skip(title, text):
            return False

        # 4. LLM Logic
        prompt = self._build_prompt(doc_type, title, text)
        result = await self._fetch_llm(prompt)
        
        # 5. Update State
        if result and result.get("found"):
            self._update_internal_maps(result, title)
            return True
            
        return False
    # --- LOGIC HELPERS ---

    def _should_skip(self, title: str, text: str) -> bool:
        if "พระราชบัญญัติ" in title: return True
        if "ยกเลิกคำสั่ง" in text[:200]: return True
        return False

    def _build_prompt(self, doc_type: str, title: str, text: str) -> str:
        template = GUIDELINE_PROMPT if doc_type == "GUIDELINE" else ORDER_PROMPT
        return template.format(
            title=title, 
            text=text,
            default_reg_name=DEFAULT_REGULATION
        )

    async def _fetch_llm(self, prompt: str) -> Optional[Dict]:
        try:
            resp = await self.llm.ainvoke(prompt)
            clean = resp.content.strip().replace("```json", "").replace("```", "")
            if "found" not in clean: return None
            return json.loads(clean)
        except Exception as e:
            print(f"LLM Error: {e}")
            return None

    def _update_internal_maps(self, extraction: Dict, source_title: str):
        # 1. Validate Regulation Name
        raw_reg = extraction.get('regulation')
        if not raw_reg or "ระเบียบ" in raw_reg: 
            reg_key = normalize_law_name(DEFAULT_REGULATION)
        else:
            reg_key = normalize_law_name(raw_reg)
            
        if "พระราชบัญญัติ" in reg_key: return

        # 2. Clean Clauses
        clauses = expand_clauses(extraction.get('clauses', []))
        
        # 3. Filter Orders (Heuristic)
        if "คำสั่ง" in source_title:
             clauses = [c for c in clauses if not (c in ["ข้อ 1", "ข้อ 2", "ข้อ 3"] and len(clauses) > 3)]

        # 4. Update Memory
        clean_title = thai_to_arabic(source_title).strip()
        
        # Update Master
        if reg_key not in self.new_master_map: self.new_master_map[reg_key] = {}
        for c in clauses:
            clean_c = re.sub(r'\s+', ' ', c).strip()
            if clean_c not in self.new_master_map[reg_key]:
                self.new_master_map[reg_key][clean_c] = []
            if clean_title not in self.new_master_map[reg_key][clean_c]:
                self.new_master_map[reg_key][clean_c].append(clean_title)

        # Update Check Map
        if clean_title not in self.new_check_map: self.new_check_map[clean_title] = []
        for c in clauses:
            clean_c = re.sub(r'\s+', ' ', c).strip()
            entry = f"{reg_key} : {clean_c}"
            if entry not in self.new_check_map[clean_title]:
                self.new_check_map[clean_title].append(entry)

    # --- OUTPUT HANDLER (Disk IO) ---

    def save_and_merge(self, master_path: str, check_path: str):
        """Merges current memory with disk files and saves."""
        if self.new_master_map:
            self._merge_file(master_path, self.new_master_map, is_master=True)
            self.new_master_map = {} # Reset
            
        if self.new_check_map:
            self._merge_file(check_path, self.new_check_map, is_master=False)
            self.new_check_map = {} # Reset

    def _merge_file(self, path: str, new_data: Dict, is_master: bool):
        existing = {}
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f: existing = json.load(f)
            except: pass

        if is_master:
            # Merge Nested Dict: Reg -> Clause -> [Files]
            for reg, clauses in new_data.items():
                if reg not in existing: existing[reg] = {}
                for clause, files in clauses.items():
                    current = set(existing[reg].get(clause, []))
                    current.update(files)
                    existing[reg][clause] = list(current)
        else:
            # Merge Simple Dict: File -> [Reg:Clause]
            for file_key, items in new_data.items():
                current = set(existing.get(file_key, []))
                current.update(items)
                existing[file_key] = list(current)

        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(existing, f, ensure_ascii=False, indent=4)
        print(f"💾 Saved: {path}")

def load_test_json(file_path: str) -> Dict:
    """Helper to simulate receiving JSON from an API/Pipeline."""
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    # Flatten chunks for the extractor
    return {
        "law_name": data[0].get("law_name", "Unknown"),
        "text": "\n".join([c.get("text", "") for c in data[:2]])
    }

import glob

async def run_local_test():
    extractor = LegalReferenceExtractor()
    
    files = glob.glob("metadata/คำสั่ง/*.json")
    
    for f in files:
        # Convert File -> JSON Object
        mock_payload = load_test_json(f) 
        
        # Feed to Engine
        await extractor.process_record(mock_payload, "GUIDELINE")

    # Save at end
    extractor.save_and_merge("storage/master.json", "storage/check.json")

if __name__ == "__main__":
    asyncio.run(run_local_test())