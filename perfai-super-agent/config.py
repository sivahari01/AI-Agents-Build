import os
from pathlib import Path
from dotenv import load_dotenv
ROOT=Path(__file__).resolve().parent
load_dotenv(ROOT/".env")
OLLAMA_BASE_URL=os.getenv("OLLAMA_BASE_URL","http://localhost:11434").rstrip("/")
OLLAMA_MODEL=os.getenv("OLLAMA_MODEL","qwen2.5:0.5b")
NEW_RELIC_API_KEY=os.getenv("NEW_RELIC_API_KEY","")
NEW_RELIC_ACCOUNT_ID=os.getenv("NEW_RELIC_ACCOUNT_ID","")
NEW_RELIC_REGION=os.getenv("NEW_RELIC_REGION","US").upper()
