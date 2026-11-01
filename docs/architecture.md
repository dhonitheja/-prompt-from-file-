# Architecture

## Overview

```
Browser (static/index.html)
        |  POST /api/prompt  (file OR url, note, provider)
        v
FastAPI (app.py)   -- blocking work runs in a thread pool
  1. file: read upload (capped at MAX_UPLOAD_MB)
     url:  sources.fetch() -> safe download (see below)
  2. prepare():  image -> as is | video -> ffmpeg frames | audio -> audio.transcribe()
                 PDF -> pypdf text | text -> utf-8 | web page -> sources.extract_page() + preview image
  3. choose provider chain, call backends in order until one succeeds
        |
        +--> Ollama    http://localhost:11434/api/chat
        +--> OpenAI    /v1/chat/completions   (and /v1/audio/transcriptions, opt-in)
        +--> Anthropic /v1/messages
```

One process, no database, no stored uploads. Files live in memory (video frames and audio in a temp dir that is deleted immediately).

## Components
- `app.py`: API, input preparation, three model adapters, provider selection.
- `sources.py`: safe link fetching (SSRF defenses) and a small HTML reader (stdlib `html.parser`).
- `audio.py`: speech-to-text, local `faster-whisper` first, OpenAI only when allowed.
- `static/index.html`: upload page with previews, link box, provider dropdown, notes, copy button.
- All model and network calls use `httpx` directly, so there is no vendor SDK dependency.

## Safe link fetching (`sources.fetch`)
For each hop (the first request and every redirect, up to 5):
1. Only `http`/`https`, only ports 80/443, a hostname is required.
2. Resolve the hostname. If **any** address is not globally routable (private, loopback, link-local, metadata, reserved, IPv4-mapped IPv6 of those), refuse.
3. Connect to the **checked IP address**, sending the real name in the `Host` header and TLS SNI. This closes the DNS-rebinding gap between "check" and "connect", while the certificate is still verified against the real name.
4. Do not auto-follow redirects; read `Location` and start again at step 1.
5. Stream the body with a byte cap (`MAX_UPLOAD_MB`) and a 20 second overall deadline.

## Non-functional requirements

| ID | Requirement | How it is checked |
|---|---|---|
| NFR-1 | Uploads and linked files over `MAX_UPLOAD_MB` (default 50) are rejected with 413 without buffering the whole body. | `test_too_large_413`, `test_link_too_large_413` |
| NFR-2 | Video processing is bounded: ffprobe 30 s, ffmpeg 120 s. | Code review; timeout returns 400 |
| NFR-3 | A bad model reply never produces a 500. | `test_malformed_model_response_is_502_not_500` |
| NFR-4 | Default mode sends no data off the machine, including audio. | `test_local_default`, `test_audio_not_sent_to_cloud_unless_chatgpt_chosen` |
| NFR-5 | Cloud requests time out (120 s) so a stuck call can't hang a worker. | Code review |
| NFR-6 | No secrets in the repo; keys come from environment variables. | `.gitignore` covers `.env`; PR review |
| NFR-7 | A link can never cause a request to a private, local or metadata address, directly or via redirect. | `test_unsafe_links_rejected` (14 cases), `test_redirect_to_private_address_rejected`, `test_hostname_resolving_to_private_address_rejected` |
| NFR-8 | One slow request does not block others. | Blocking work runs in a thread pool (`run_in_threadpool`) |
| NFR-9 | Hosted mode cannot start without a password of 12+ characters, and every route except `/healthz` requires it. | `tests/test_auth.py`; CI "Refuses to start without a password" step |
| NFR-10 | Every reply carries anti-framing and content-security headers. | `test_security_headers_always_present` |

## Decisions

**ADR-1: Local model by default.** Privacy is the main differentiator, and it costs nothing to run. Cloud models are opt-in through API keys.

**ADR-2: Plain HTTP instead of vendor SDKs.** Small adapters over `httpx` keep dependencies minimal and the install fast. Trade-off: we track API shape changes ourselves.

**ADR-3: Auto fallback order is local, ChatGPT, Claude.** Matches the owner's stated preference. Providers without a key are skipped, so Auto never silently sends data anywhere unless a key was configured.

**ADR-4: Sample frames for video instead of sending video.** Works with every vision model. Trade-off: motion is inferred from frames, and the audio track is ignored. `VIDEO_FRAMES` is configurable.

**ADR-5: One shared password, enforced in the app.** Local use stays open. Setting `APP_PASSWORD` turns on HTTP Basic auth for everything except `/healthz`, and the Docker image sets `HOSTED=1` so it cannot start without a strong password (fail closed). Chosen over user accounts because this is a single-owner tool; trade-off: no per-user control or rate limiting (T18).

**ADR-9: Docker image, platform-neutral.** A plain Dockerfile (non-root user, ffmpeg included, `$PORT` aware, `/healthz` health check) runs on any container host. `render.yaml` is an optional convenience for Render.

**ADR-6: Links are read as metadata, not played or run.** Reading title, description, text and the preview image works for almost any site, app store or game page without a browser engine, accounts or heavy dependencies. Trade-off: JavaScript-only pages yield little. A headless-browser mode could be added later but would widen the attack surface.

**ADR-7: Audio is transcribed locally; cloud transcription is opt-in.** Audio often contains private speech. Cloud transcription is used only when ChatGPT is chosen explicitly or `ALLOW_CLOUD_TRANSCRIPTION=1`. `faster-whisper` is an optional install because it pulls in large dependencies.

**ADR-8: Pin the connection to the validated IP.** Checking a hostname and then letting the HTTP library resolve it again would allow DNS rebinding. Connecting to the checked address with the original `Host`/SNI avoids that without extra dependencies.
