import asyncio
import logging
from typing import Any
from langchain_core.output_parsers import StrOutputParser
from src.app.chatbot.prompts.routing import build_prompt
from src.app.chatbot.prompts.legal_routing import build_prompt as build_legal_routing_prompt

from src.app.chatbot.constants import (
    ROUTE_GENERAL,
    ROUTE_FILE_REQUEST,
    ROUTE_LEGAL_QUERY,
    HISTORY_WINDOW,
    LLM_TIMEOUT_SECONDS,
    LEGAL_ROUTE_ORDER,
    LEGAL_ROUTE_GUIDELINE, 
    LEGAL_ROUTE_STANDARD,
    LEGAL_ROUTE_REGULATION,
)

logger = logging.getLogger(__name__)

_routing_prompt = build_prompt()

async def get_top_level_route(
    query: str,
    history: list,
    llm: Any,
) -> str:
    history_str = _format_history(history)

    chain = _routing_prompt | llm | StrOutputParser()

    try:
        decision = await asyncio.wait_for(
            chain.ainvoke({"history": history_str, "query": query}),
            timeout=LLM_TIMEOUT_SECONDS,
        )
        route = _parse_route(decision.strip().upper())
        logger.debug(f"Routing decision: '{decision.strip()}' → {route}")
        return route

    except asyncio.TimeoutError:
        logger.error("get_top_level_route timed out — defaulting to LEGAL_RAG")
        return ROUTE_LEGAL_QUERY

    except Exception as e:
        logger.error(f"get_top_level_route failed — defaulting to LEGAL_RAG: {e}", exc_info=True)
        return ROUTE_LEGAL_QUERY


def _parse_route(decision: str) -> str:
    """
    Maps the raw LLM output string to a known route constant.
    Checked in priority order — most specific first.
    Falls back to LEGAL_RAG if nothing matches.
    """
    if ROUTE_GENERAL in decision:     return ROUTE_GENERAL
    if ROUTE_FILE_REQUEST in decision: return ROUTE_FILE_REQUEST
    return ROUTE_LEGAL_QUERY


def _format_history(history: list) -> str:
    """
    Serializes the last N messages for prompt injection.
    Caps each message at 500 chars to avoid blowing the context window.
    """
    if not history:
        return "No history."

    return "\n".join(
        f"{msg.type}: {msg.content[:500]}"
        for msg in history[-HISTORY_WINDOW:]
    )

_legal_routing_prompt = build_legal_routing_prompt() 

async def get_legal_sub_route(
    query: str,
    history: list,
    llm: Any,
) -> str:
    """
    Classifies a legal query into:
    REGULATION, ORDER, GUIDELINE, STANDARD, or GENERAL.

    Public so the evaluator can call it directly without going
    through the full handler pipeline.
    """
    history_str = _format_history(history)
    chain = _legal_routing_prompt | llm | StrOutputParser()

    try:
        decision = await asyncio.wait_for(
            chain.ainvoke({"history": history_str, "query": query}),
            timeout=LLM_TIMEOUT_SECONDS,
        )
        route = _parse_legal_route(decision.strip().upper())
        logger.debug(f"Legal routing decision: '{decision.strip()}' → {route}")
        return route

    except asyncio.TimeoutError:
        logger.error("get_legal_sub_route timed out — defaulting to GENERAL")
        return "GENERAL"

    except Exception as e:
        logger.error(f"get_legal_sub_route failed — defaulting to GENERAL: {e}", exc_info=True)
        return "GENERAL"


def _parse_legal_route(decision: str) -> str:
    if LEGAL_ROUTE_STANDARD in decision:   return LEGAL_ROUTE_STANDARD
    if LEGAL_ROUTE_ORDER in decision:      return LEGAL_ROUTE_ORDER
    if LEGAL_ROUTE_GUIDELINE in decision:  return LEGAL_ROUTE_GUIDELINE
    if LEGAL_ROUTE_REGULATION in decision: return LEGAL_ROUTE_REGULATION
    return "GENERAL"