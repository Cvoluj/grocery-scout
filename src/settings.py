
from itertools import cycle
import os
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()

BASE_DIR = Path(__file__).parent.parent.resolve()
SHARED_DATA = BASE_DIR / "shared_data"
SHARED_DATA.mkdir(exist_ok=True)

BROWSER_TYPES = ["chrome99", "chrome100", "chrome101", "chrome104", "chrome107", "chrome110", "chrome116", "chrome119", "chrome120", "chrome123", "chrome124", "chrome131", "chrome133a", "chrome136", "chrome142", "chrome145", "chrome146", "chrome99_android", "chrome131_android"]
BROWSER_TYPES_CYCLE = cycle(BROWSER_TYPES)

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")



ATB_SHOPS_CACHE = SHARED_DATA / "atb_shops.json"
VARUS_SHOPS_CACHE = SHARED_DATA / "varus_shops.json"

LLM_SERVICE_URL = os.getenv("LLM_SERVICE_URL", "http://llm-matcher:8001")
LLM_SERVICE_API_KEY = os.environ["LLM_SERVICE_API_KEY"]

if __name__ == '__main__':
    print(BASE_DIR)