# Architecture

## Overview

```
Browser (static/index.html)
        |  POST /api/prompt  (file, note, provider)
        v
FastAPI (app.py)
  1. read upload (capped at MAX_UPLOAD_MB)
  2. prepare(): image -> as is | video -> ffmpeg frames | PDF -> pypdf text | text -> utf-8
  3. choose provider chain, call backends in order until one succeeds
        |
        +--> Ollama   http://localhost:11434/api/chat
        +--> OpenAI   /v1/chat/completions
        +--> Anthropic /v1/messages
```

One process, no database, no stored uploads. Files live in memory (video frames in a temp dir that is deleted immediately).

## Components
- `app.py`: API, file preparation, three backend adapters, provider selection.
- `static/index.html`: upload page with preview, provider dropdown, copy button.
- All backend calls use `httpx` directly, so there is no vendor SDK dependency.

## Non-functional requirements

| ID | Requirement | How it is checked |
|---|---|---|
| NFR-1 | Uploads over `MAX_UPLOAD_MB` (default 50) are rejected with 413 without buffering the whole body. | `test_too_large_413` |
| NFR-2 | Video processing is bounded: ffprobe 30 s, ffmpeg 120 s. | Code review; timeout returns 400 |
| NFR-3 | A bad model reply never produces a 500. | `test_malformed_model_response_is_502_not_500` |
| NFR-4 | Default mode sends no data off the machine. | `test_local_default`; keys unset means no cloud call |
| NFR-5 | Cloud requests time out (120 s) so a stuck call can't hang the server. | Code review |
| NFR-6 | No secrets in the repo; keys come from environment variables. | CI diff review, `.gitignore` covers `.env` |

## Decisions

**ADR-1: Local model by default.** Privacy is the main differentiator, and it costs nothing to run. Cloud models are opt-in through API keys.

**ADR-2: Plain HTTP instead of vendor SDKs.** Three small adapters over `httpx` keep dependencies minimal and the install fast. Trade-off: we track API shape changes ourselves.

**ADR-3: Auto fallback order is local, ChatGPT, Claude.** Matches the owner's stated preference. Providers without a key are skipped, so Auto never silently sends data anywhere unless a key was configured.

**ADR-4: Sample frames for video instead of sending video.** Works with every vision model. Trade-off: motion is inferred from frames, so fast action can be missed. `VIDEO_FRAMES` is configurable.

**ADR-5: No authentication in this version.** The tool is meant to run locally. Hosting it publicly requires a proxy with auth (documented in `SECURITY.md`).
