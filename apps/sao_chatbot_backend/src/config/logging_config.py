import logging
import sys
from pathlib import Path

def setup_logging():
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d - %(message)s',
        handlers=[
            logging.FileHandler("logs/app.log", encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )

    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("httpx").setLevel(logging.WARNING)

    logging.info("Logging system initialized.")