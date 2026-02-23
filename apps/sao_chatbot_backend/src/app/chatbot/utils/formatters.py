import re
from typing import List, Dict


def thai_to_arabic(text: str) -> str:
    """Converts Thai numerals to Arabic numerals for consistent mapping."""
    thai_digits = "๐๑๒๓๔๕๖๗๘๙"
    arabic_digits = "0123456789"
    translation_table = str.maketrans(thai_digits, arabic_digits)
    return text.translate(translation_table)

def arabic_to_thai(text: str) -> str:
    """Standardizes text by converting all Thai numerals to Arabic."""
    if not text: return ""
    thai_digits = "๐๑๒๓๔๕๖๗๘๙"
    arabic_digits = "0123456789"
    translation_table = str.maketrans(arabic_digits, thai_digits)
    return text.translate(translation_table).strip()

def normalize_regulation_id(raw_id: str) -> str:
        """
        Strips chunk suffixes to return the clean Clause ID.
        Example: "ข้อ ๑๔_p2" -> "ข้อ ๑๔"
        Example: "Clause 1_p10" -> "Clause 1"
        """
        if not raw_id: return ""
        return re.sub(r'_p\d+$', '', str(raw_id)).strip()

def clean_clause_id(raw_id: str) -> str:
    if not raw_id: return "ไม่ระบุข้อ"
    return re.sub(r'_p\d+$', '', raw_id).strip()

def format_regulation_context(docs: List[Dict]) -> str:
    if not docs: return "No context found."
    
    formatted_output = []
    for i, doc in enumerate(docs, 1):
        ref_id = f"REG_{i}"
        law_name = doc.get('law_name', 'Unknown Regulation')
        clause_no = clean_clause_id(doc.get('id', ''))
        main_text = doc.get('text', '')
        
        content = [
            f"### [{ref_id}]",
            f"Source Name: {law_name}",
            f"Clause/ID: {clause_no}",
            f"Content: {main_text}"
        ]
        
        # Related Guidelines/Orders
        related = doc.get('related_documents', [])
        if related:
            content.append("\n--- RELATED GUIDELINES/ORDERS ---")
            for j, rel in enumerate(related, 1):
                guide_id = f"{ref_id}_SUB_{j}"
                content.append(f"[{guide_id}] Title: {rel.get('law_name')}\nContent: {rel.get('text')}")
        
        formatted_output.append("\n".join(content))
            
    return "\n\n====================\n\n".join(formatted_output)   
