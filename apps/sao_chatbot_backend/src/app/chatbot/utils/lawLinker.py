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

