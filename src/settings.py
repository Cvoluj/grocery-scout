
from itertools import cycle
import os
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

BASE_DIR = Path(__file__).parent.parent.resolve()
SHARED_DATA = BASE_DIR / "shared_data"
SHARED_DATA.mkdir(exist_ok=True)

BROWSER_TYPES = ["chrome99", "chrome100", "chrome101", "chrome104", "chrome107", "chrome110", "chrome116", "chrome119", "chrome120", "chrome123", "chrome124", "chrome131", "chrome133a", "chrome136", "chrome142", "chrome145", "chrome146", "chrome99_android", "chrome131_android"]
BROWSER_TYPES_CYCLE = cycle(BROWSER_TYPES)


ATB_SHOPS_CACHE = SHARED_DATA / "atb_shops.json"
VARUS_SHOPS_CACHE = SHARED_DATA / "varus_shops.json"

LLM_SERVICE_URL = os.getenv("LLM_SERVICE_URL", "http://llm-matcher:8001")
LLM_SERVICE_API_KEY = os.environ["LLM_SERVICE_API_KEY"]

PB_ENCRYPTION_KEY=os.getenv("PB_ENCRYPTION_KEY")
PB_ADMIN_EMAIL=os.getenv("PB_ADMIN_EMAIL")
PB_ADMIN_PASSWORD=os.getenv("PB_ADMIN_PASSWORD")
PB_URL = os.getenv("PB_URL")

class RuntimeSettings:
    def __init__(self):
        self._data: dict = {}

    def load(self, settings: dict):
        self._data = settings

    def get(self, key: str, default: str = "") -> str:
        return self._data.get(key, default)

    def __getitem__(self, key: str) -> str:
        return self._data[key]
runtime = RuntimeSettings()

if __name__ == '__main__':
    print(BASE_DIR)