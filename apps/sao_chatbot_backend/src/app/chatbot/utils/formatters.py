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
    
        if "ระเบียบ" in law_name:
            full_ref = f"ข้อ {clause_no} {law_name}" if clause_no else law_name
        else:
            full_ref = law_name

        content = [
            f"### [{ref_id}] REFERENCE_LABEL: {full_ref}",
            f"Source Name: {law_name}",
            f"Clause/ID: {clause_no}",
            f"Content: {doc.get('text', '')}"
        ]
        
        related = doc.get('related_documents', [])
        if related:
            content.append("\n--- RELATED GUIDELINES/ORDERS ---")
            for j, rel in enumerate(related, 1):
                rel_name = rel.get('law_name', '')
                content.append(f"[{ref_id}_SUB_{j}] Title: {rel_name}\nContent: {rel.get('text')}")
        
        formatted_output.append("\n".join(content))
            
    return "\n\n====================\n\n".join(formatted_output)

def simplify_thai_text(text: str) -> str:
    """Converts to Arabic AND removes all whitespace for a 'pure' string match."""
    if not text: return ""
    text = thai_to_arabic(text)
    text = re.sub(r'[\s\u00A0\t\n\r]+', '', text)
    return text