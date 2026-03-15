from .general import build_prompt as build_chitchat_prompt
from .file_request import build_prompt as build_file_request_prompt
from .legal_query import build_prompt as build_legal_rag_prompt
from .routing import build_prompt as build_routing_prompt
from .legal_routing import build_prompt as build_legal_routing_prompt

__all__ = [
    "build_chitchat_prompt",
    "build_file_request_prompt",
    "build_legal_rag_prompt",
    "build_routing_prompt",
    "build_legal_routing_prompt",
]