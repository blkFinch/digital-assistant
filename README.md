# digital-assistant

## Getting Started

### Prerequisites
- Python 3.10 or higher
- Virtual environment recommended

### Installation
1. Clone the repository and navigate to the project directory.
2. Create and activate a virtual environment:
   ```powershell
   python3 -m venv .venv
   .venv\Scripts\Activate.ps1  # On Windows
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. For GPU support with EasyOCR (optional, for faster OCR):
   ```bash
   pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
   ```

### Running the Dev Cockpit (REPL)
The dev cockpit is an interactive REPL for testing the AI agent.

1. Start the REPL:
   ```bash
   python -m core_agent.app.transport.repl_client
   ```
2. Use commands like:
   - `/help` - Show available commands
   - `/new` - Start a new session
   - `/verbose on` - Enable debug output and prompt dumping
   - Type any message to interact with the AI

### Debug Logs and Prompt Dumps
- **Debug Logs**: Enable with `--debug` flag or `/verbose on` in REPL. Logs are written to the console and can be configured via `core_agent/app/utils/logger.py`.
- **Prompt Dumps**: When debug is enabled, prompts sent to the LLM are saved to `core_agent/logs/latest_prompt.txt` and `latest_reflection_prompt.txt`. This helps inspect what the AI is seeing and processing.
- Session data is stored in `core_agent/data/sessions/` as JSON files.

### Personality Selection (swappable personas)
The assistant’s personality is loaded from a prompt file. You can switch it without code changes via env vars (the app loads `.env` via `python-dotenv`).

- `PERSONALITY_NAME` — resolves to `core_agent/app/resources/prompts/personalities/<PERSONALITY_NAME>.md`
  - Nested names are allowed (e.g. `anime/yuki`)

Examples:
- `PERSONALITY_NAME=yuki`
- `PERSONALITY_NAME=anime/yuki`

Default (when unset): `core_agent/app/resources/prompts/personality.md`

### Long-Term Memory Selection (swappable LTM)
You can isolate long-term memory per profile without changing code.

- `LTM_NAME` — routes LTM + revision log to:
  - `core_agent/data/ltm/<LTM_NAME>/ltm.json`
  - `core_agent/data/ltm/<LTM_NAME>/revision_log.jsonl`
- Default (when unset):
  - `core_agent/data/sessions/ltm.json`
  - `core_agent/data/sessions/revision_log.jsonl`

Notes:
- Session files are stamped with `ltm_name`; resuming a session under a different `LTM_NAME` will fail fast.
- `core_agent/data/ltm/` is gitignored by default.

## Notes on EasyOCR
- make sure to install the correct torchvision if you have a nvidia gpu to utilize cuda


## Notes on Python Env
```powershell
python3 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install easyocr
python main.py
```