import datetime
from typing import Final

#System main route
ROUTE_GENERAL: Final = "GENERAL"
ROUTE_FILE_REQUEST: Final = "FILE_REQUEST"
ROUTE_LEGAL_QUERY: Final = "LEGAL_QUERY"

TOP_LEVEL_ROUTES = frozenset([
    ROUTE_GENERAL,
    ROUTE_FILE_REQUEST,
    ROUTE_LEGAL_QUERY,
])

#Retriver route
LEGAL_ROUTE_REGULATION: Final = "REGULATION"
LEGAL_ROUTE_ORDER: Final = "ORDER"
LEGAL_ROUTE_GUIDELINE: Final = "GUIDELINE"
LEGAL_ROUTE_STANDARD: Final = "STANDARD"
LEGAL_ROUTE_GENERAL: Final = "GENERAL"

#Constant value
FUZZY_MATCH_THRESHOLD: Final = 65
DEFAULT_RETRIEVAL_K: Final = 3
HISTORY_WINDOW: Final = 5
LLM_TIMEOUT_SECONDS: Final = 300.0

#Retrieval
DEFAULT_RETRIEVE_K = 3
RELATED_DOCS_K = 3
FETCH_MULTIPLIER = 5

#RRF score
RRF_C: Final = 60   

#File Path
REGULATION_PATH = "storage/regulations"
OTHERS_PATH = "storage/others"
MASTER_MAP_PATH = "storage/master_map.json"
SOURCE_MAP_PATH = "storage/source_map.json"

# Date filtering sentinels
DATE_FORMAT = "%Y-%m-%d"
DATE_MIN = datetime.datetime(1000, 1, 1)
DATE_MAX = datetime.datetime(9999, 12, 31)
