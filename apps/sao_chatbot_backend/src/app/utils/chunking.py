import os
import re
import json
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from langchain_text_splitters import RecursiveCharacterTextSplitter

max_chunk_size = 1100
chunk_overlap = 200

THAI_DIGITS = "๐๑๒๓๔๕๖๗๘๙"

INLINE_VERSION_PATTERN = re.compile(
    r"\((?:เพิ่มเติม|ยกเลิก|แก้ไข)โดยฉบับที่\s*([๐-๙]+)\s+พ\.ศ\.\s*[๐-๙]+\)"
)
SECTION_HEADER_PATTERN = re.compile(
    r"ฉบับที่\s*([๐-๙]+)\)"
)

def thai_to_int(thai_str: str) -> int:
    return int(thai_str.translate(str.maketrans(THAI_DIGITS, "0123456789")))

def detect_chunk_version(text_lines: List[str], section_version: Optional[int], default_version: int) -> int:
    if section_version is not None:
        return section_version
    for line in text_lines:
        match = INLINE_VERSION_PATTERN.search(line)
        if match:
            return thai_to_int(match.group(1))
    return 1


def build_version_to_source_map(sources: list) -> Dict[int, str]:
    return {s["order"]: s["source_id"] for s in sources}

def extract_header_and_footer(text: str) -> Tuple[str, List[str], List[str]]:
    raw_lines = text.split('\n')

    references = []
    ref_pattern = re.compile(
        r"^\s*[\(\[]?\s*(เอกสาร|สิ่งที่ส่งมาด้วย|แบบ|อ้างถึง)?.*?\.(docx|doc|pdf|xlsx|xls|ppt|pptx)$",
        re.IGNORECASE
    )
    clean_lines = raw_lines[:]

    while clean_lines:
        last_line = clean_lines[-1].strip()
        if not last_line:
            clean_lines.pop()
            continue
        if ref_pattern.match(last_line):
            references.insert(0, last_line)
            clean_lines.pop()
        else:
            break

    law_name = "Unknown"
    body_lines = []
    found_name = False

    for line in clean_lines:
        if not found_name and line.strip():
            law_name = line.strip()
            found_name = True
            continue
        if found_name:
            body_lines.append(line)

    return law_name, references, body_lines


def chunk_by_size(
    text: str,
    law_name: Optional[str] = None,
    announce_date: Optional[str] = None,
    effective_date: Optional[str] = None,
    expire_date: Optional[str] = None,
    version: int = 1,
    document_id: Optional[str] = None,
    doc_type: str = None,
) -> List[Dict]:
    ext_law_name, ext_refs, lines = extract_header_and_footer(text)

    final_law_name = law_name if law_name is not None else ext_law_name
    full_body_text = "\n".join(lines).strip()
    splitter = RecursiveCharacterTextSplitter(
        separators=["\n\n", "\n", " ", ""],
        chunk_size=max_chunk_size,
        chunk_overlap=chunk_overlap
    )

    text_chunks = splitter.split_text(full_body_text)
    json_results = []

    for i, chunk_text in enumerate(text_chunks):
        json_results.append({
            "id": f"Chunk_{i+1}",
            "document_id": document_id,
            "original_document_id": document_id, 
            "law_name": final_law_name,
            "text": chunk_text,
            "doc_type": doc_type,
            "announce_date": announce_date,
            "effective_date": effective_date,
            "expire_date": expire_date,
            "version": version,
            "metadata": {
                "หมวด": "บททั่วไป",
                "ส่วน": "",
                "chunk_index": i
            }
        })
    return json_results


def chunk_by_clause(
    text: str,
    law_name: Optional[str] = None,
    announce_date: Optional[str] = None,
    effective_date: Optional[str] = None,
    expire_date: Optional[str] = None,
    version: int = 1,
    document_id: Optional[str] = None,
    doc_type: str = None,
    version_to_source: Optional[Dict[int, str]] = None, 
) -> List[Dict]:

    ext_law_name, ext_refs, lines = extract_header_and_footer(text)
    final_law_name = law_name if law_name is not None else ext_law_name

    clause_pattern    = re.compile(r"^(ข้อ\s+[๐-๙]+)")
    chapter_pattern   = re.compile(r"^หมวด\s+[๐-๙]+")
    part_pattern      = re.compile(r"^ส่วนที่\s+[๐-๙]+")
    separator_pattern = re.compile(r"^---\s*$")

    splitter = RecursiveCharacterTextSplitter(
        separators=["\n\n", "\n", " ", ""],
        chunk_size=max_chunk_size,
        chunk_overlap=chunk_overlap
    )

    json_results       = []
    current_clause_id  = "Preamble"
    current_text_lines = []
    current_chapter    = "บททั่วไป"
    current_part       = ""
    section_version    = None  

    def resolve_original_document_id(chunk_version: int) -> Optional[str]:
        if not version_to_source:
            return document_id        
        return version_to_source.get(chunk_version)

    def create_dict(cid, text_content, chap, part,
                    chunk_version, original_document_id, is_sub=False):
        is_merged = version_to_source is not None
        return {
            "id":                   cid,
            "document_id":          document_id,
            "original_document_id": original_document_id,
            "law_name":             final_law_name,
            "text":                 text_content,
            "doc_type":             doc_type,
            "announce_date":        announce_date,
            "effective_date":       effective_date,
            "expire_date":          expire_date,
            "version":              version,
            "metadata": {
                "หมวด":       chap,
                "ส่วน":       part,
                "char_count": len(text_content),
                "is_split":   is_sub,
                **( {"chunk_version": chunk_version} if is_merged else {} ),
            },
        }

    def process_buffer(cid, lines_list, chap, part):
        full_text = "\n".join(lines_list).strip()
        if not full_text:
            return

        chunk_version        = detect_chunk_version(lines_list, section_version, version)
        original_document_id = resolve_original_document_id(chunk_version)

        if len(full_text) > max_chunk_size:
            sub_chunks = splitter.split_text(full_text)
            for i, sub_text in enumerate(sub_chunks):
                json_results.append(
                    create_dict(f"{cid}_p{i+1}", sub_text, chap, part,
                                chunk_version, original_document_id, is_sub=True)
                )
        else:
            json_results.append(
                create_dict(cid, full_text, chap, part,
                            chunk_version, original_document_id)
            )

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        if separator_pattern.match(stripped):
            if current_text_lines:
                process_buffer(
                    current_clause_id, current_text_lines,
                    current_chapter, current_part
                )
                current_text_lines = []
                current_clause_id  = "Preamble"
            continue

        if stripped.startswith("**ข้อความ"):
            header_match = SECTION_HEADER_PATTERN.search(stripped)
            if header_match:
                section_version = thai_to_int(header_match.group(1))
            continue

        if chapter_pattern.match(stripped):
            current_chapter = stripped
            current_part    = ""
        elif part_pattern.match(stripped):
            current_part = stripped

        match = clause_pattern.match(stripped)
        if match:
            if current_text_lines:
                process_buffer(
                    current_clause_id, current_text_lines,
                    current_chapter, current_part
                )
            current_clause_id  = match.group(1)
            current_text_lines = [stripped]
        else:
            current_text_lines.append(stripped)

    if current_text_lines:
        process_buffer(
            current_clause_id, current_text_lines,
            current_chapter, current_part
        )

    return json_results


def process_folders(input_root: str, output_root: str, metadata_file: str = "metadata.json"):
    input_path = Path(input_root)
    output_path = Path(output_root)

    metadata_lookup = {}
    if os.path.exists(metadata_file):
        with open(metadata_file, 'r', encoding='utf-8') as f:
            metadata_lookup = json.load(f)
        print(f"Loaded metadata for {len(metadata_lookup)} files.")

    folder_map = {
        "ระเบียบ": chunk_by_clause,
        "คำสั่ง": chunk_by_size,
        "แนวทาง": chunk_by_size,
        "หลักเกณฑ์": chunk_by_size
    }

    for folder_name, chunk_func in folder_map.items():
        input_dir = input_path / folder_name
        if not input_dir.exists():
            continue

        print(f"Processing '{folder_name}'...")
        output_dir = output_path / folder_name
        os.makedirs(output_dir, exist_ok=True)

        for file_path in input_dir.glob("*.txt"):
            try:
                file_meta = metadata_lookup.get(file_path.name, {})

                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                chunks = chunk_func(
                    text=content,
                    law_name=file_meta.get("law_name"),
                    announce_date=file_meta.get("announce"),
                    effective_date=file_meta.get("effective"),
                    expire_date=file_meta.get("expire"),
                    version=int(file_meta.get("version", 1)),
                    doc_type=folder_name,
                    # version_to_source not passed → non-merged doc behavior
                )

                out_name = output_dir / f"{file_path.stem}_metadata.json"
                with open(out_name, 'w', encoding='utf-8') as f:
                    json.dump(chunks, f, ensure_ascii=False, indent=4)

                print(f"  -> Saved {len(chunks)} chunks: {out_name.name}")

            except Exception as e:
                print(f"  ! Error processing {file_path.name}: {e}")