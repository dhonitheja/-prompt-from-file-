# Prompt from File

Upload an image, video, PDF or text file and get back the prompt that could recreate it, ready to paste into an AI image, video or text tool.

It runs on a **local model through [Ollama](https://ollama.com)** by default, so your files never leave your machine. If the local model fails, it can fall back to **ChatGPT (OpenAI)**.

## What you get

For each upload the app returns:

- **Prompt:** one polished, paste-ready prompt (subject, style, composition, lighting, color, mood, and camera or motion for video)
- **Negative prompt:** what to avoid (images and video only)
- **Key details:** a few bullets on what drove the prompt

## Supported files

| Type | How it is handled | Needs |
|---|---|---|
| Images (JPEG, PNG, GIF, WebP) | Sent to the model directly | Vision model |
| Video | Sampled into evenly spaced frames, sent together | Vision model, `ffmpeg` |
| PDF | Text is extracted and sent | Any model |
| Text and code (`.txt`, `.md`, `.csv`, `.json`, `.py`, `.js`, ...) | Sent as text | Any model |

Audio is not supported yet.

## Quick start

**Prerequisites:** Python 3.10+, [Ollama](https://ollama.com), and `ffmpeg` if you want video.

```bash
# 1. Pull a vision model
ollama pull llama3.2-vision        # or qwen2.5vl, llava, gemma3

# 2. Install and run
git clone https://github.com/dhonitheja/-prompt-from-file-.git prompt-from-file
cd prompt-from-file
pip install -r requirements.txt
uvicorn app:app --reload
```

Open http://localhost:8000, drop a file on the page, and click **Generate prompt**. Add optional context in the text box, such as "for Midjourney".

## Choosing a model: local, ChatGPT or Claude

Three backends are supported. Add an API key for the cloud ones you want:

```bash
export OPENAI_API_KEY=sk-...          # enables ChatGPT
export ANTHROPIC_API_KEY=sk-ant-...   # enables Claude
uvicorn app:app --reload
```

Pick one on the page (Auto, Local only, ChatGPT only, Claude only), or per request with the `provider` field (`auto`, `ollama`, `openai`, `claude`). To change the default for every request, set `LLM_PROVIDER`.

**Auto** tries the local model first. If it is unreachable or errors, it tries ChatGPT, then Claude, skipping any whose key isn't set. The response's `provider` field tells you which one answered.

Note: when a cloud model runs, the file is sent to that service rather than staying on your machine. Leave the API keys unset to keep everything local.

## Configuration

All settings are environment variables.

| Variable | Default | Description |
|---|---|---|
| `LLM_PROVIDER` | `auto` | `auto` (local, then ChatGPT, then Claude), `ollama`, `openai` or `claude` |
| `OLLAMA_MODEL` | `llama3.2-vision` | Any Ollama vision model |
| `OLLAMA_URL` | `http://localhost:11434` | Where Ollama is running |
| `OPENAI_API_KEY` | none | Enables ChatGPT |
| `OPENAI_MODEL` | `gpt-4o-mini` | Any vision-capable OpenAI model |
| `ANTHROPIC_API_KEY` | none | Enables Claude |
| `CLAUDE_MODEL` | `claude-sonnet-5-5` | Model used for Claude |
| `VIDEO_FRAMES` | `6` | Frames sampled per video |
| `MAX_UPLOAD_MB` | `50` | Upload size limit |

## API

```bash
curl -F "file=@photo.jpg" -F "note=for Midjourney" http://localhost:8000/api/prompt
```

`POST /api/prompt` takes multipart form data:

- `file` (required): the upload
- `note` (optional): extra context for the model
- `provider` (optional): `auto`, `ollama`, `openai` or `claude`; defaults to `LLM_PROVIDER`

Response:

```json
{
  "filename": "photo.jpg",
  "type": "image/jpeg",
  "provider": "ollama",
  "prompt": "**Prompt:** ..."
}
```

Errors return JSON with a `detail` message: `415` for an unsupported type, `413` for a file over the size limit, `502` if the model backend can't be reached.

## Security

The app has no login. Run it on your own machine, or put it behind an authenticating proxy. See [SECURITY.md](SECURITY.md).

## Development

```bash
pip install -r requirements-dev.txt
ruff check .
pytest -q
```

Tests mock all model backends, so they need no Ollama or API keys. See [CONTRIBUTING.md](CONTRIBUTING.md).

## Project layout

```
app.py             FastAPI backend and model calls
static/index.html  Upload page
tests/             API tests (backends mocked)
docs/              PRD, architecture, threat model, test plan, project status
.github/workflows  CI: lint, tests, dependency scan
```

## Tips and limits

- Prompt quality depends on the model. Small models like `llava` give rougher results than `qwen2.5vl`, ChatGPT or Claude.
- A local model sees only the sampled video frames, so motion and camera work are inferred from them. Raise `VIDEO_FRAMES` for longer videos, at the cost of speed.
- The first request can be slow while Ollama loads the model.
- The result is an educated reconstruction, not the original prompt. The app describes what is visible and does not recover hidden metadata.
