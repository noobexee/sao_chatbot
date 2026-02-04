import os
import re
import json
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from langchain_text_splitters import RecursiveCharacterTextSplitter

max_chunk_size = 1100
chunk_overlap = 200
def extract_header_and_footer(text: str) -> Tuple[str, List[str], List[str]]:
    """
    Extracts the Law Name (first line) and References (attachments at bottom).
    Returns: (law_name, reference_list, body_lines)
    """
    raw_lines = text.split('\n')
    
    # 1. Extract References (Bottom up)
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
            
    # 2. Extract Law Name (First non-empty line)
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
            "law_name": final_law_name,
            "text": chunk_text,
            "doc_type": "แนวทาง",
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
) -> List[Dict]:
    ext_law_name, ext_refs, lines = extract_header_and_footer(text)
    final_law_name = law_name if law_name is not None else ext_law_name

    clause_pattern = re.compile(r"^(ข้อ\s+[๐-๙]+)")
    chapter_pattern = re.compile(r"^หมวด\s+[๐-๙]+")
    part_pattern = re.compile(r"^ส่วนที่\s+[๐-๙]+")

    splitter = RecursiveCharacterTextSplitter(
        separators=["\n\n", "\n", " ", ""],
        chunk_size=max_chunk_size,
        chunk_overlap=chunk_overlap
    )
    
    json_results = []
    current_clause_id = "Preamble"
    current_text_lines = []
    current_chapter, current_part = "บททั่วไป", ""

    def process_buffer(cid, lines_list, chap, part):
        full_text = "\n".join(lines_list).strip()
        if not full_text: return

        # If the specific Clause is over 2000 chars, split it up
        if len(full_text) > max_chunk_size:
            sub_chunks = splitter.split_text(full_text)
            for i, sub_text in enumerate(sub_chunks):
                json_results.append(create_dict(f"{cid}_p{i+1}", sub_text, chap, part, is_sub=True))
        else:
            json_results.append(create_dict(cid, full_text, chap, part))

    def create_dict(cid, text_content, chap, part, is_sub=False):
        return {
            "id": cid,
            "document_id": document_id,
            "law_name": final_law_name,
            "text": text_content,
            "doc_type": "ระเบียบ",
            "announce_date": announce_date,
            "effective_date": effective_date,
            "expire_date": expire_date,
            "version": version,
            "metadata": {
                "หมวด": chap, 
                "ส่วน": part,
                "char_count": len(text_content),
                "is_split": is_sub
            },
        }

    for line in lines:
        stripped = line.strip()
        if not stripped: continue
            
        if chapter_pattern.match(stripped):
            current_chapter, current_part = stripped, ""
        elif part_pattern.match(stripped):
            current_part = stripped
        
        match = clause_pattern.match(stripped)
        if match:
            if current_text_lines:
                process_buffer(current_clause_id, current_text_lines, current_chapter, current_part)
            current_clause_id = match.group(1)
            current_text_lines = [stripped]
        else:
            current_text_lines.append(stripped)

    if current_text_lines:
        process_buffer(current_clause_id, current_text_lines, current_chapter, current_part)
        
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
        "แนวทาง": chunk_by_size
    }
    
    for folder_name, chunk_func in folder_map.items():
        input_dir = input_path / folder_name
        if not input_dir.exists(): continue 
            
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
                )
                
                out_name = output_dir / f"{file_path.stem}_metadata.json"
                with open(out_name, 'w', encoding='utf-8') as f:
                    json.dump(chunks, f, ensure_ascii=False, indent=4)
                    
                print(f"  -> Saved {len(chunks)} chunks: {out_name.name}")
                
            except Exception as e:
                print(f"  ! Error processing {file_path.name}: {e}")
