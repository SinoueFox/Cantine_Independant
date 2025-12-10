import logging
from config import LOG_PATH
from datetime import datetime

def log_error(message: str):
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(f"{datetime.now().isoformat()} - {message}\n")

logger = logging.getLogger("CANTINE")
logger.setLevel(logging.INFO)

handler = logging.FileHandler(LOG_PATH)
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)

logger.addHandler(handler)