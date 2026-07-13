import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


ROOT_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT_DIR / "data"
RESOURCES_DIR = ROOT_DIR / "app" / "resources"
SESSIONS_DIR = DATA_DIR / "sessions"
LOGS_DIR = ROOT_DIR / "logs"

# Long-term memory (LTM)
#
# Default (backwards compatible): keep LTM under data/sessions/
# If LTM_NAME is set: route LTM + revision log under data/ltm/<LTM_NAME>/
LTM_ROOT_DIR = DATA_DIR / "ltm"
DEFAULT_LTM_PATH = SESSIONS_DIR / "ltm.json"
DEFAULT_REVISION_LOG_PATH = SESSIONS_DIR / "revision_log.jsonl"

DEFAULT_PERSONALITY_PATH = RESOURCES_DIR / "prompts" / "personality.md"
PERSONALITIES_DIR = RESOURCES_DIR / "prompts" / "personalities"


def resolve_personality_path() -> Path:
	"""Select which personality prompt file to use.

	Precedence:
	1) PERSONALITY_NAME (resolved under app/resources/prompts/personalities)
	2) default: app/resources/prompts/personality.md
	"""
	name = (os.getenv("PERSONALITY_NAME") or "").strip()
	if name:
		name_path = Path(name)
		if name_path.is_absolute():
			raise RuntimeError(
				"Invalid PERSONALITY_NAME: must be a relative name like 'yuki' or 'anime/yuki' "
				"(no absolute paths)."
			)

		candidate = (PERSONALITIES_DIR / name_path)
		if candidate.suffix == "":
			candidate = candidate.with_suffix(".md")

		# Fail fast + enforce in-repo sandbox: the resolved path must stay under PERSONALITIES_DIR.
		personalities_root = PERSONALITIES_DIR.resolve()
		resolved = candidate.resolve()
		try:
			resolved.relative_to(personalities_root)
		except ValueError as e:
			raise RuntimeError(
				f"Invalid PERSONALITY_NAME '{name}': resolved path must be inside {personalities_root}"
			) from e

		if not resolved.exists():
			raise RuntimeError(
				f"Personality not found for PERSONALITY_NAME='{name}'. Expected file: {resolved}"
			)
		return resolved

	return DEFAULT_PERSONALITY_PATH


PERSONALITY_PATH = resolve_personality_path()
REFLECTION_PROMPT_PATH = RESOURCES_DIR / "prompts" / "reflection_prompt.txt"
PROMPT_MESSAGE_LIMIT = int(os.getenv("PROMPT_MESSAGE_LIMIT", "15"))
REFLECTION_MESSAGE_LIMIT = int(os.getenv("REFLECTION_MESSAGE_LIMIT", "10"))

MAX_SCREEN_CONTEXTS = int(os.getenv("MAX_SCREEN_CONTEXTS", "5"))

def resolve_ltm_paths():
	"""Resolve which LTM store + revision log to use based on LTM_NAME.

	- If LTM_NAME is unset/blank: use DEFAULT_* paths under data/sessions/.
	- If set: use data/ltm/<LTM_NAME>/ltm.json and revision_log.jsonl

	This validates that LTM_NAME is a *relative* path and that resolution stays
	within LTM_ROOT_DIR to prevent directory traversal.
	"""
	name = (os.getenv("LTM_NAME") or "").strip()
	if not name:
		return "", DEFAULT_LTM_PATH, DEFAULT_REVISION_LOG_PATH

	name_path = Path(name)
	if name_path.is_absolute():
		raise RuntimeError(
			"Invalid LTM_NAME: must be a relative name like 'yuki_ltm' or 'stream/yuki' "
			"(no absolute paths)."
		)

	candidate_dir = (LTM_ROOT_DIR / name_path)
	ltm_root = LTM_ROOT_DIR.resolve()
	resolved_dir = candidate_dir.resolve()
	try:
		resolved_dir.relative_to(ltm_root)
	except ValueError as e:
		raise RuntimeError(
			f"Invalid LTM_NAME '{name}': resolved path must be inside {ltm_root}"
		) from e

	return name, (resolved_dir / "ltm.json"), (resolved_dir / "revision_log.jsonl")


# Debugging / audit + memory store routing
LTM_NAME, LTM_PATH, REVISION_LOG_PATH = resolve_ltm_paths()

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

ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# TTS configuration
TTS_PROVIDER = os.getenv("TTS_PROVIDER", "openai")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini-tts")
TTS_VOICE = os.getenv("TTS_VOICE", "alloy")
TTS_FORMAT = os.getenv("TTS_FORMAT", "wav")
TTS_SAMPLE_RATE = int(os.getenv("TTS_SAMPLE_RATE", "24000"))