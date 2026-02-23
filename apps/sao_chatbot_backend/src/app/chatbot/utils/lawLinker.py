import re
import json
from typing import List, Dict

class LawLinker:
    def __init__(self, json_path: str = "storage/master_map.json"):
        self.map_data = self._load_json(json_path)

    def _normalize_law_name(self, raw_name: str) -> str:
        """
        Strips version and year to find the 'Concept' Name.
        """
        if not raw_name: return ""
        
        # 1. Remove (ฉบับที่ ...) including Thai/Arabic digits
        # Matches (ฉบับที่ ๒), (ฉบับที่ 2), etc.
        name = re.sub(r'\s*\(ฉบับที่.*?\)', '', raw_name)
        
        # 2. Remove พ.ศ. ... to end of string
        name = re.sub(r'\s*พ\.ศ\..*', '', name)
        
        # 3. Clean up extra spaces
        return name.strip()

    def _normalize_section(self, section_id: str) -> str:
        """
        Ensures 'ข้อ ๕๓' and 'ข้อ 53' match.
        (Simple example: just returns string, but you can add Thai digit conversion here)
        """
        return section_id.strip()

    def get_linked_orders(self, regulation_doc: Dict) -> List[str]:
        """
        Takes ANY version of a Regulation Document and finds its linked Orders.
        """
        raw_law_name = regulation_doc.get("law_name", "")
        section_id = regulation_doc.get("id", "") # e.g., "ข้อ 53"

        # 1. Normalize to find the Key
        base_name = self._normalize_law_name(raw_law_name)
        clean_section = self._normalize_section(section_id)

        print(f"DEBUG: Looking up -> Law: '{base_name}' | Section: '{clean_section}'")

        # 2. Look up in Master Map
        if base_name in self.master_map:
            law_group = self.master_map[base_name]
            
            # Check if this specific section has links
            if clean_section in law_group:
                return law_group[clean_section]
        
        return []

linker = LawLinker()

# CASE 1: The 2025 Version (ฉบับที่ ๒)
doc_v2 = {
    "id": "ข้อ 53",
    "law_name": "ระเบียบสำนักงานการตรวจเงินแผ่นดินว่าด้วยการตรวจสอบการปฏิบัติตามกฎหมาย (ฉบับที่ ๒) พ.ศ. ๒๕๖๘",
    "text": "..."
}

# CASE 2: The 2023 Version (The Original)
doc_v1 = {
    "id": "ข้อ 53",
    "law_name": "ระเบียบสำนักงานการตรวจเงินแผ่นดินว่าด้วยการตรวจสอบการปฏิบัติตามกฎหมาย พ.ศ. ๒๕๖๖",
    "text": "..."
}

# CASE 3: A Different Law entirely
doc_diff = {
    "id": "ข้อ 4",
    "law_name": "ระเบียบสำนักงานการตรวจเงินแผ่นดินว่าด้วยการปฏิบัติหน้าที่ของเจ้าหน้าที่ที่ได้รับมอบหมาย พ.ศ. 2562",
    "text": "..."
}

print("--- Test Case 1: 2025 Version ---")
links_1 = linker.get_linked_orders(doc_v2)
print(f"Result: {links_1}") 
# Expected: matches the base name, returns Order 20/2566

print("\n--- Test Case 2: 2023 Version ---")
links_2 = linker.get_linked_orders(doc_v1)
print(f"Result: {links_2}") 
# Expected: matches the SAME base name, returns SAME Order 20/2566

print("\n--- Test Case 3: Different Law ---")
links_3 = linker.get_linked_orders(doc_diff)
print(f"Result: {links_3}")