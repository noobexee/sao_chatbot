import re
import logging
from typing import List, Dict

from pythainlp import word_tokenize

from src.app.chatbot.prompts.query_rewrite import build_prompt as build_rewrite_prompt
from src.app.chatbot.prompts.keyword_extract import build_prompt as build_keyword_prompt

logger = logging.getLogger(__name__)

def _build_history_context(history: List[Dict]) -> str:
    """Formats recent chat history into a readable context string."""
    context_lines = []
    for msg in history[-4:]:
        if hasattr(msg, "content"):
            role = "User" if msg.type == "human" else "Assistant"
            content = msg.content
        elif isinstance(msg, dict):
            role = "User" if msg.get("role") == "user" else "Assistant"
            content = msg.get("content", "")
        else:
            continue
        context_lines.append(f"{role}: {content}")
    return "\n".join(context_lines)


async def rewrite_query_with_history(
    llm, query: str, history: List[Dict]
) -> str:
    """
    Uses the LLM to rewrite a follow-up query into a standalone search query
    by resolving references against the chat history.
    Returns the original query if history is empty or rewriting fails.
    """
    if not history:
        return query
 
    try:
        prompt = build_rewrite_prompt()
        chain = prompt | llm
        response = await chain.ainvoke({
            "history": _build_history_context(history),
            "query": query,
        })
        rewritten = response.content.strip() if hasattr(response, "content") else str(response)
        rewritten = rewritten.replace('"', "").replace("Query:", "").strip()
        return rewritten or query
 
    except Exception as e:
        logger.error(f"Query rewriting failed: {e}")
        return query


async def extract_keywords(llm, query_text: str) -> List[str]:
    try:
        prompt = build_keyword_prompt()
        chain = prompt | llm
        response = await chain.ainvoke({"query": query_text})
        raw_text = response.content.strip() if hasattr(response, "content") else str(response)
 
        keywords = [k.strip() for k in re.split(r"[,|\n]", raw_text) if k.strip()]
        keywords = [
            re.sub(r"^(Keywords|คำสำคัญ):\s*", "", k, flags=re.IGNORECASE).strip()
            for k in keywords
        ]
        return keywords or word_tokenize(query_text, engine="newmm")
    
    except Exception as e:
        logger.error(f"Keyword extraction failed for '{query_text}': {e}")
        return word_tokenize(query_text, engine="newmm")
