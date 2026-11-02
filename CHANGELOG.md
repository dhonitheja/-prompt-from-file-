# Changelog

## Unreleased

### Added
- Target tool: choose Midjourney, Stable Diffusion/Flux, ChatGPT image, text-to-video, voiceover, app builder or chat assistant, and the prompt is written in that tool's style. New `target` field in the API and a dropdown on the page.
- Hosting: `Dockerfile`, `render.yaml`, a `/healthz` endpoint and `docs/deploy.md`.
- Password login (`APP_PASSWORD`) for every page and API route except `/healthz`. Hosted mode (`HOSTED=1`, set in the image) refuses to start without a password of 12+ characters.
- Security headers on every reply (CSP, anti-framing, `nosniff`, no referrer).
- CI builds the Docker image and smoke-tests it.
- Links: paste a website, app store, game or video page and get a prompt from its title, description, text and preview image. Direct links to image, video, audio, PDF and text files work too.
- Audio files: speech is transcribed (local `faster-whisper`, or OpenAI if you choose ChatGPT) and turned into a prompt.
- A `notes` field in the response that says what could not be analyzed.
- Upload an image, video, PDF or text file and get a reverse-engineered prompt.
- Providers: local Ollama (default), ChatGPT and Claude, with an Auto mode that falls back in that order.
- Provider selector on the upload page and a `provider` API field.
- Tests, CI (lint, tests, dependency scan), and project docs.

### Changed
- The response field `filename` is now `source` (a file name or a link).
- Model calls, downloads and ffmpeg now run off the main event loop, so one slow request no longer blocks others.

### Security
- Link fetching blocks private, local and cloud-metadata addresses, checks every redirect, and pins the connection to the checked address.
- Uploads are read up to the size limit only, instead of buffering the whole body first.
- Video processing has timeouts and checks for both `ffmpeg` and `ffprobe`.
- A malformed reply from a model returns a clean 502 instead of a 500.
