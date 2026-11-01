# Prompt from File

Upload a file or paste a link and get back the prompt that could recreate it, ready to paste into an AI image, video, audio, writing or app-building tool.

It works with images, video, audio, PDFs, text and code, and links to websites, apps, games and videos.

It runs on a **local model through [Ollama](https://ollama.com)** by default, so your files never leave your machine. If the local model fails, it can fall back to **ChatGPT (OpenAI)** or **Claude**.

## What you get

- **Prompt:** one polished, paste-ready prompt (subject, style, composition, lighting, color, mood, and camera or motion for video; purpose, features, screens and style for a website, app or game)
- **Negative prompt:** what to avoid (images and video only)
- **Key details:** a few bullets on what drove the prompt
- **Notes:** what the app could and could not look at (for example "audio track not analyzed")

## What it accepts

| Input | How it is handled | Needs |
|---|---|---|
| Images (JPEG, PNG, GIF, WebP), including game screenshots | Sent to the model directly | Vision model |
| Video | Sampled into evenly spaced frames, sent together | Vision model, `ffmpeg` |
| Audio (MP3, WAV, M4A, FLAC, OGG) | Speech is transcribed, then turned into a prompt | `faster-whisper` (local), or ChatGPT |
| PDF | Text is extracted and sent | Any model |
| Text and code | Sent as text | Any model |
| Link to a website, app store page, game page or video page | The page's title, description, text and preview image are read | Vision model for the preview image |
| Link straight to an image, video, audio, PDF or text file | Downloaded, then handled like an upload | As above |

**What links can and can't do.** For a game, app or video page the app reads what the page says about itself. It does not play the video, run the app or log in. Pages that build everything with JavaScript, or sit behind a login, may give little or nothing, and the response says so. Game and app files themselves (executables, ROMs, installers) are not supported; use a screenshot, a gameplay video or the store link.

**What audio can and can't do.** Only speech is understood. Music, tone of voice and sound effects are not analyzed, and a file with no speech returns a clear message instead of a made-up prompt.

## Quick start

**Prerequisites:** Python 3.10+, [Ollama](https://ollama.com), and `ffmpeg` if you want video.

```bash
# 1. Pull a vision model
ollama pull llama3.2-vision        # or qwen2.5vl, llava, gemma3

# 2. Install and run
git clone https://github.com/dhonitheja/-prompt-from-file-.git prompt-from-file
cd prompt-from-file
pip install -r requirements.txt
pip install -r requirements-audio.txt   # optional: local speech-to-text for audio
uvicorn app:app --reload
```

Open http://localhost:8000, then drop a file or paste a link and click **Generate prompt**. Add optional context in the text box, such as "for Midjourney".

## Choosing a model: local, ChatGPT or Claude

Three backends are supported. Add an API key for the cloud ones you want:

```bash
export OPENAI_API_KEY=sk-...          # enables ChatGPT
export ANTHROPIC_API_KEY=sk-ant-...   # enables Claude
uvicorn app:app --reload
```

Pick one on the page (Auto, Local only, ChatGPT only, Claude only), or per request with the `provider` field (`auto`, `ollama`, `openai`, `claude`). To change the default for every request, set `LLM_PROVIDER`.

**Auto** tries the local model first. If it is unreachable or errors, it tries ChatGPT, then Claude, skipping any whose key isn't set. The response's `provider` field tells you which one answered.

**Privacy.** When a cloud model runs, what you sent (the file, or the page details from a link) goes to that service. Leave the API keys unset to keep everything local. Audio is stricter: it is transcribed on your machine, and is only sent to OpenAI for transcription if you pick **ChatGPT only** (or set `ALLOW_CLOUD_TRANSCRIPTION=1`). Links are fetched by the server you run, not by the cloud models.

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
| `WHISPER_MODEL` | `base` | Local speech-to-text model size (`tiny`, `base`, `small`, `medium`, `large-v3`) |
| `ALLOW_CLOUD_TRANSCRIPTION` | unset | Set to `1` to let audio go to OpenAI for transcription in any mode |
| `VIDEO_FRAMES` | `6` | Frames sampled per video |
| `MAX_UPLOAD_MB` | `50` | Size limit for uploads and linked files |

## API

```bash
# a file
curl -F "file=@photo.jpg" -F "note=for Midjourney" http://localhost:8000/api/prompt

# a link
curl -F "url=https://example.com/my-game" http://localhost:8000/api/prompt
```

`POST /api/prompt` takes multipart form data. Send **either** `file` **or** `url`:

- `file`: the upload
- `url`: an http or https link
- `note` (optional): extra context for the model
- `provider` (optional): `auto`, `ollama`, `openai` or `claude`; defaults to `LLM_PROVIDER`

Response:

```json
{
  "source": "photo.jpg",
  "type": "image/jpeg",
  "provider": "ollama",
  "notes": [],
  "prompt": "**Prompt:** ..."
}
```

`source` is the file name or the link you sent. Errors return JSON with a `detail` message:

| Code | Meaning |
|---|---|
| 400 | Bad request: missing or double input, empty file, unusable video, a link that is invalid or points to a private address |
| 413 | File or linked file over the size limit |
| 415 | Unsupported file type |
| 422 | Nothing could be read: a page with no content, or audio with no speech |
| 501 | Audio needs speech-to-text and none is set up |
| 502 | A model or the linked site could not be reached or gave a bad reply |

## Security

The app has no login. Run it on your own machine, or put it behind an authenticating proxy. Links are fetched with protections against requests to private networks. See [SECURITY.md](SECURITY.md).

## Development

```bash
pip install -r requirements-dev.txt
ruff check .
pytest -q
```

Tests mock all model backends and network access, so they need no Ollama, API keys or internet. See [CONTRIBUTING.md](CONTRIBUTING.md).

## Project layout

```
app.py             FastAPI backend, file and page preparation, model calls
sources.py         Safe link fetching and page reading
audio.py           Speech-to-text
static/index.html  Upload page
tests/             API tests (models and network mocked)
docs/              PRD, architecture, threat model, test plan, project status
.github/workflows  CI: lint, tests, dependency scan
```

## Tips and limits

- Prompt quality depends on the model. Small models like `llava` give rougher results than `qwen2.5vl`, ChatGPT or Claude.
- A local model sees only the sampled video frames, so motion and camera work are inferred from them. The video's audio track is not analyzed. Raise `VIDEO_FRAMES` for longer videos, at the cost of speed.
- The first request can be slow while Ollama (or the Whisper model) loads.
- The result is an educated reconstruction, not the original prompt. The app describes what it can see or read and does not recover hidden metadata.
