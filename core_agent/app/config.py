import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


ROOT_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT_DIR / "data"
SESSIONS_DIR = DATA_DIR / "sessions"
LOGS_DIR = ROOT_DIR / "logs"
PERSONALITY_PATH = DATA_DIR / "personality.md"
REFLECTION_PROMPT_PATH = DATA_DIR / "reflection_prompt.txt"
PROMPT_MESSAGE_LIMIT = int(os.getenv("PROMPT_MESSAGE_LIMIT", "15"))
REFLECTION_MESSAGE_LIMIT = int(os.getenv("REFLECTION_MESSAGE_LIMIT", "10"))

MAX_SCREEN_CONTEXTS = int(os.getenv("MAX_SCREEN_CONTEXTS", "5"))

# Debugging / audit
REVISION_LOG_PATH = SESSIONS_DIR / "revision_log.jsonl"

# Memory gating
MIN_MEMORY_CONFIDENCE = float(os.getenv("MIN_MEMORY_CONFIDENCE", "0.4"))

# OpenRouter configuration
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_BASE_URL = os.getenv(
	"OPENROUTER_BASE_URL",
	"https://openrouter.ai/api/v1/chat/completions",
)
OPENROUTER_DEFAULT_MODEL = os.getenv("OPENROUTER_DEFAULT_MODEL", "openrouter/auto")
OPENROUTER_APP_NAME = os.getenv("OPENROUTER_APP_NAME", "memory-test")
OPENROUTER_SITE_URL = os.getenv("OPENROUTER_SITE_URL", "")
OPENROUTER_REQUEST_TIMEOUT = float(os.getenv("OPENROUTER_REQUEST_TIMEOUT", "30"))