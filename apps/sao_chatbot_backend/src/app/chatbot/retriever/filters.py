import logging
from datetime import datetime
from typing import Dict, List, Optional

from src.app.chatbot.constants import DATE_FORMAT, DATE_MAX, DATE_MIN

logger = logging.getLogger(__name__)


def _parse_date(val, is_expiry: bool = False) -> datetime:
    """
    Parses a date string into a datetime object.
    Returns DATE_MAX for missing expiry dates and DATE_MIN for missing effective dates,
    so documents with no dates are always considered valid.
    """
    sentinel = DATE_MAX if is_expiry else DATE_MIN

    if val is None:
        return sentinel

    s_val = str(val).strip().lower()
    if s_val in {"", "none", "null", "nan"}:
        return sentinel

    return datetime.strptime(s_val, DATE_FORMAT)


def _get_target_date(search_date: Optional[str]) -> datetime:
    """
    Returns the date to filter against.
    - If search_date is provided, parse and use it.
    - Otherwise, default to today converted to Buddhist Era (พ.ศ.).
    """
    now = datetime.now()
    default = datetime(now.year + 543, now.month, now.day)

    if not search_date:
        return default

    try:
        return datetime.strptime(search_date, DATE_FORMAT)
    except ValueError:
        logger.warning(f"Invalid search_date format '{search_date}', defaulting to today.")
        return default


def _is_valid_on_date(doc: Dict, target_dt: datetime) -> bool:
    """Returns True if the document is in effect on the given target date."""
    eff_dt = _parse_date(doc.get("effective_date"), is_expiry=False)
    exp_dt = _parse_date(doc.get("expire_date"), is_expiry=True)
    return eff_dt <= target_dt <= exp_dt


def filter_by_date(
    candidates: List[Dict],
    k: int,
    search_date: Optional[str] = None,
) -> List[Dict]:
    """
    Filters candidates to documents valid on search_date (defaults to today in พ.ศ.),
    deduplicates by (law_name, id), and returns up to k results.
    """
    target_dt = _get_target_date(search_date)
    filtered: List[Dict] = []
    seen_keys: set = set()

    for doc in candidates:
        unique_key = f"{doc.get('law_name', '')}|{doc.get('id') or doc.get('document_id', '')}"

        if unique_key in seen_keys:
            continue

        try:
            if _is_valid_on_date(doc, target_dt):
                filtered.append(doc)
                seen_keys.add(unique_key)
        except Exception as e:
            logger.error(f"Error filtering document '{unique_key}': {e}")
            continue

        if len(filtered) >= k:
            break

    return filtered