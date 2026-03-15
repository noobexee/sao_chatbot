import re
import logging
from typing import Any, Dict, List, Optional

from src.app.chatbot.utils.formatters import simplify_thai_text, thai_to_arabic, normalize_regulation_id
from .filters import filter_by_date
from .search import (
    run_rrf_fusion,
    vector_search_other,
    keyword_search_other,
)
from src.app.chatbot.constants import DEFAULT_RETRIEVE_K, FETCH_MULTIPLIER
  
logger = logging.getLogger(__name__)

def get_parent_regulations(source_map: Dict, other_doc: Dict) -> List[Dict[str, str]]:
    """
    Returns a list of {reg_name, section} dicts that the given other-document
    references, looked up via the source map.
    """
    if not source_map:
        return []

    doc_title = other_doc.get("law_name", "").strip()
    parent_references = []

    for entry in source_map.get(doc_title, []):
        if ":" in entry:
            name_part, section_part = entry.split(":", 1)
            parent_references.append({"reg_name": name_part.strip(), "section": section_part.strip()})
        else:
            parent_references.append({"reg_name": entry.strip(), "section": ""})

    return parent_references


def _is_exact_regulation_match(target_name: str, target_section_raw: str, reg_meta: Dict) -> bool:
    """
    Returns True if reg_meta corresponds to the regulation identified by
    target_name and target_section_raw.
    """
    if target_name not in reg_meta.get("law_name", ""):
        return False

    if not target_section_raw:
        return True  

    target_section_norm = normalize_regulation_id(target_section_raw)
    meta_id_norm = normalize_regulation_id(reg_meta.get("id", ""))

    t_base_match = re.search(r"(ข้อ\s*\d+)", target_section_norm)
    t_base = t_base_match.group(1) if t_base_match else target_section_norm.split()[0]

    m_base_match = re.search(r"(ข้อ\s*\d+)", meta_id_norm)
    m_base = m_base_match.group(1) if m_base_match else meta_id_norm.split("_")[0]

    if t_base != m_base:
        return False

    t_sub_match = re.search(r"\(\d+\)", target_section_norm)
    if t_sub_match:
        t_sub = t_sub_match.group(0)
        t_sub_thai = t_sub.translate(str.maketrans("0123456789", "๐๑๒๓๔๕๖๗๘๙"))
        text_content = reg_meta.get("text", "")
        if t_sub not in text_content and t_sub_thai not in text_content:
            return False

    return True


def fetch_exact_parent_regulations(
    source_map: Dict,
    reg_metadata: List[Dict],
    cand: Dict,
    search_date: Optional[str] = None,
    k: int =  DEFAULT_RETRIEVE_K
) -> List[Dict]:
    """
    Finds and returns the regulation chunks that are the exact parents of
    the given other-document candidate.
    """
    parents = get_parent_regulations(source_map, cand)
    if not parents:
        return []

    matched_parents = [
        reg_meta
        for p in parents
        for reg_meta in reg_metadata
        if _is_exact_regulation_match(p.get("reg_name", ""), p.get("section", ""), reg_meta)
    ]

    return filter_by_date(matched_parents, k=DEFAULT_RETRIEVE_K, search_date=search_date)


def get_related_document_titles(master_map: Dict, reg_doc: Dict) -> List[str]:
    """
    Returns the list of other-document titles that are mapped to the given
    regulation document via the master map.
    """
    if not master_map:
        return []

    full_law_name = reg_doc.get("law_name", "")
    core_law = re.sub(r"\(ฉบับที่.*?\)|พ\.ศ\..*$", "", full_law_name).strip()
    norm_core_law = simplify_thai_text(core_law)

    law_mapping = {}
    for map_law_name, clauses in master_map.items():
        norm_map = simplify_thai_text(map_law_name)
        if norm_core_law in norm_map or norm_map in norm_core_law:
            law_mapping = clauses
            break

    if not law_mapping:
        return []

    reg_id_digits = re.findall(r"[๐-๙0-9]+", normalize_regulation_id(reg_doc.get("id", "")))
    base_num = thai_to_arabic(reg_id_digits[0]) if reg_id_digits else ""

    text_content = reg_doc.get("text", "")
    sub_clause_match = re.search(r"^\s*\(([๐-๙0-9]+)\)", text_content)
    sub_num = thai_to_arabic(sub_clause_match.group(1)) if sub_clause_match else None

    all_titles = []
    for map_key, titles in law_mapping.items():
        map_key_arabic = thai_to_arabic(map_key)
        if sub_num:
            if base_num in map_key_arabic and f"({sub_num})" in map_key_arabic:
                all_titles.extend(titles)
        elif re.search(rf"\b{base_num}\b", map_key_arabic):
            all_titles.extend(titles)

    return list(set(all_titles))


async def fetch_related_other_documents(
    master_map: Dict,
    embedder,
    other_index,
    other_bm25,
    other_metadata: List[Dict],
    reg: Dict,
    effective_query: str,
    keywords: List[str],
    seen_in_related: set,
    search_date: Optional[str] = None,
    k: int = DEFAULT_RETRIEVE_K,
) -> List[Dict]:
    """
    Searches other documents related to a regulation chunk by:
    1. Looking up allowed titles via the master map.
    2. Running a hybrid search and filtering to only those allowed titles.
    """
    allowed_titles = get_related_document_titles(master_map, reg)
    if not allowed_titles:
        return []

    normalized_allowed = [simplify_thai_text(t) for t in allowed_titles]

    fetch_k = DEFAULT_RETRIEVE_K * FETCH_MULTIPLIER
    vec_res = vector_search_other(embedder, other_index, effective_query, fetch_k)
    key_res = keyword_search_other(other_bm25, keywords, fetch_k)
    candidates = run_rrf_fusion(vec_res, key_res, other_metadata, fetch_k)

    filtered_related = []
    for cand in candidates:
        norm_cand_name = simplify_thai_text(cand.get("law_name", ""))
        is_match = any(
            nt in norm_cand_name or norm_cand_name in nt for nt in normalized_allowed
        )
        if is_match:
            unique_key = f"{cand.get('law_name')}|{cand.get('id')}"
            filtered_related.append(cand)
            seen_in_related.add(unique_key)

    return filter_by_date(filtered_related, k=DEFAULT_RETRIEVE_K, search_date=search_date)
