# LLM → TTS WebSocket Service

Backend service that accepts text over WebSocket, asks an OpenAI chat model for a reply, turns the reply into speech, and returns the generated audio as a binary frame.

## Features
- `/ws` WebSocket endpoint that validates JSON payloads and returns `audio/mpeg` bytes.
- `/healthz` and `/version` HTTP endpoints for readiness checks.
- Modular services for OpenAI Chat and TTS calls with configurable timeouts.
- Structured JSON logging.
- Async test client (`client/test_client.py`) for manual verification.

## Requirements
- Python 3.11+
- OpenAI API key with Chat + TTS access (`OPENAI_API_KEY`).

## Installation
Create and activate a virtual environment, then install dependencies:

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install .[dev]
```

If you use `uv`, you can instead run:

```bash
uv sync --extra dev
```

## Configuration
Copy the sample below into `.env` (or export the variables):

```env
OPENAI_API_KEY=sk-your-key
CHAT_MODEL=gpt-4o-mini
TTS_MODEL=tts-1
TTS_VOICE=alloy
LOG_LEVEL=info
PORT=8000
MAX_TEXT_LENGTH=1000
WS_INACTIVITY_TIMEOUT=30
CHAT_TIMEOUT=10
TTS_TIMEOUT=20
```

## Running the Service

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

The WebSocket endpoint is available at `ws://localhost:8000/ws`.

## Manual Testing
Use the bundled client to send text and save the resulting audio:

```bash
python client/test_client.py --text "Hello there" --save output.mp3
```

## Tests
Run the automated test suite:

```bash
pytest
```

## Troubleshooting
- **400 errors / validation:** Ensure payload is JSON with a non-empty `text` field.
- **Timeouts:** Adjust `CHAT_TIMEOUT`, `TTS_TIMEOUT`, or `WS_INACTIVITY_TIMEOUT` as needed.
- **Missing dependencies:** Verify the virtual environment is active before installing or running commands.
