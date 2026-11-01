# Prompt from File

Upload an image, video, PDF or text file and get a reverse-engineered prompt. Runs on a **local model via Ollama** by default, so nothing leaves your machine.

## Run locally

```bash
# 1. Install Ollama (https://ollama.com) and pull a vision model
ollama pull llama3.2-vision      # or qwen2.5vl, llava, gemma3

# 2. Start the app
pip install -r requirements.txt
uvicorn app:app --reload
```

Open http://localhost:8000. Videos need `ffmpeg` installed.

## Settings (env vars)

| Var | Default | Notes |
|---|---|---|
| `LLM_PROVIDER` | `ollama` | `claude` switches to the Claude API (needs `ANTHROPIC_API_KEY`) |
| `OLLAMA_MODEL` | `llama3.2-vision` | any Ollama vision model |
| `OLLAMA_URL` | `http://localhost:11434` | |
| `VIDEO_FRAMES` | `6` | frames sampled per video |
| `MAX_UPLOAD_MB` | `50` | |

## API

`POST /api/prompt` (multipart): `file`, optional `note` -> `{ filename, type, provider, prompt }`

Notes: images and video need a vision-capable model; PDFs and text work with any model (PDFs use extracted text). Audio isn't supported.
