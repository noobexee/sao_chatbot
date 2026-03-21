from typing import Any


def map_references_to_document_ids(
    retrieved_docs: list[dict[str, Any]],
    refs_list: list[str],
) -> dict[str, str | None]:
    """
    Maps LLM-generated reference strings to their document IDs
    using the metadata from retrieved documents.
    """
    print(retrieved_docs)
    doc_mapping = _build_doc_mapping(retrieved_docs)
    print(doc_mapping)

    return {
        ref: _find_best_match(ref, doc_mapping)
        for ref in refs_list
    }


def _build_doc_mapping(retrieved_docs: list[dict[str, Any]]) -> dict[str, str]:
    """Flattens retrieved docs and their related docs into a single name→id map."""
    mapping = {}

    for doc in retrieved_docs:
        if "law_name" in doc and "original_document_id" in doc:
            mapping[doc["law_name"]] = doc["original_document_id"]

        for related in doc.get("related_documents", []):
            if "law_name" in related and "original_document_id" in related:
                mapping[related["law_name"]] = related["original_document_id"]

    return mapping


def _find_best_match(ref: str, doc_mapping: dict[str, str]) -> str | None:
    """
    Finds the most specific match for a reference string.
    Prefers longer matches to avoid partial name collisions
    e.g. "ระเบียบ สตง. 2566" should win over "ระเบียบ สตง."
    """
    matches = [
        db_name for db_name in doc_mapping
        if db_name in ref or ref in db_name
    ]

    if not matches:
        return None

    best = max(matches, key=len)
    return doc_mapping[best]