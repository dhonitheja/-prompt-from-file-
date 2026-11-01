# Hosting Prompt from File

The app ships as a Docker image. It starts in **hosted mode** (`HOSTED=1`), which refuses to start unless `APP_PASSWORD` is set to at least 12 characters, and then asks for that password in the browser.

## What changes when it is hosted

- **There is no local model.** Hosted servers don't run Ollama, so you need at least one cloud key (`OPENAI_API_KEY` for ChatGPT, `ANTHROPIC_API_KEY` for Claude).
- **Privacy is different.** Files and links you submit go to your server and then to the cloud model. The "everything stays on your machine" default only applies when you run it locally.
- **Audio:** there is no local speech-to-text on the hosted image. To transcribe audio, set `OPENAI_API_KEY` and either pick "ChatGPT only" on the page or set `ALLOW_CLOUD_TRANSCRIPTION=1`. Without that, audio uploads return a clear 501.
- **One shared password**, not user accounts. Anyone who has it can spend your API credits. Use a long random value and rotate it if it leaks.

## Option A: Render (few clicks)

1. Push the repo to GitHub (done).
2. In Render: **New -> Blueprint**, choose this repo. It reads `render.yaml`.
3. When prompted, paste your `OPENAI_API_KEY` and/or `ANTHROPIC_API_KEY`.
4. After the first deploy, open the service's **Environment** tab and copy the generated `APP_PASSWORD`.
5. Open the service URL. Your browser asks for a login: any username, and that password.

Notes: the free plan sleeps when idle, so the first request after a pause is slow. Render provides HTTPS. `render.yaml` has not been deployed from here, so if the Blueprint complains, create a **Web Service** from the repo with runtime **Docker** and set the same variables by hand, with health check path `/healthz`.

## Option B: any host that runs Docker

```bash
docker build -t prompt-from-file .
docker run -p 8000:8000 \
  -e APP_PASSWORD="$(openssl rand -base64 24)" \
  -e OPENAI_API_KEY=sk-... \
  prompt-from-file
```

The container listens on `$PORT` (default 8000) and has a `/healthz` endpoint that needs no login, for platform health checks. Put it behind HTTPS (most platforms do this for you). The login uses HTTP Basic auth, so without HTTPS the password travels in clear text.

## Environment variables for hosting

| Variable | Required | Description |
|---|---|---|
| `APP_PASSWORD` | yes | Login password, at least 12 characters |
| `OPENAI_API_KEY` | one of these | Enables ChatGPT (and audio transcription if allowed) |
| `ANTHROPIC_API_KEY` | one of these | Enables Claude |
| `LLM_PROVIDER` | no | `auto` by default. In hosted mode the local model is skipped quickly because Ollama isn't there |
| `ALLOW_CLOUD_TRANSCRIPTION` | no | `1` to let audio be transcribed by OpenAI in any mode |
| `MAX_UPLOAD_MB` | no | Upload limit (default 50). Your platform may enforce its own smaller limit |

## After deploying: checklist

1. Open the URL without logging in: you should be asked for a password.
2. Log in and upload a small image: you should get a prompt and "Answered by: ChatGPT" (or Claude).
3. Paste a public web page link: you should get a prompt with a note that it is based on page metadata.
4. Paste `http://169.254.169.254/`: you should get a "private or local address" error.
5. Watch your OpenAI/Anthropic usage for the first few days.

## Known limits of this setup

- No per-user accounts and no rate limiting. A leaked or guessed password means anyone can use your credits. Choose a long password; consider your provider's spending caps.
- No logs of who used it, and no stored uploads.
- A single instance; nothing is shared between restarts (there is nothing to lose, as no data is kept).
