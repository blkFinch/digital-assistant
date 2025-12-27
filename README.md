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

## Notes on EasyOCR
- make sure to install the correct torchvision if you have a nvidia gpu to utilize cuda


## Notes on Python Env
```powershell
python3 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install easyocr
python main.py
```