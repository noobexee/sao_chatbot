from .base import BaseHandler
from .general import GeneralHandler
from .file_request import FileRequestHandler
from .legal_query import LegalRagHandler

__all__ = [
    "GeneralHandler",
    "FileRequestHandler",
    "LegalRagHandler",
    "BaseHandler",
]