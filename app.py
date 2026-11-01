"""Turn a file or a link into a reverse-engineered prompt.

Accepts images, video, audio, PDFs, text/code, and links (web pages, app and game pages,
videos, direct file links). Runs on a local model via Ollama by default. If it fails, the
request falls back to ChatGPT, then Claude, for whichever API keys are set.
"""
import base64
import io
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from urllib.parse import urljoin, urlsplit

import httpx
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from audio import transcribe
from sources import HTML_TYPES, describe, extract_page, fetch

PROVIDER = os.getenv("LLM_PROVIDER", "auto").lower()  # "auto", "ollama", "openai" or "claude"
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2-vision")  # any vision model: qwen2.5vl, llava, gemma3...
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")  # any vision-capable OpenAI model
OPENAI_URL = os.getenv("OPENAI_URL", "https://api.openai.com/v1/chat/completions")
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-sonnet-5-5")
CLAUDE_URL = os.getenv("CLAUDE_URL", "https://api.anthropic.com/v1/messages")
MAX_BYTES = int(os.getenv("MAX_UPLOAD_MB", "50")) * 1024 * 1024
VIDEO_FRAMES = int(os.getenv("VIDEO_FRAMES", "6"))
PREVIEW_IMAGE_BYTES = 10 * 1024 * 1024

IMAGE_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"}
TEXT_EXTS = {".txt", ".md", ".csv", ".json", ".py", ".js", ".ts", ".html", ".css", ".xml", ".yaml", ".yml", ".log"}
AUDIO_EXTS = {".mp3", ".wav", ".m4a", ".ogg", ".oga", ".flac", ".aac", ".opus"}

SYSTEM = """You reverse-engineer prompts. Given a file, frames from a video, an audio transcript, or details
from a web page, write the prompt someone could give an AI tool to recreate it.

Respond in this format:
**Prompt:** one polished, ready-to-paste prompt (subject, style, composition, lighting, color, mood,
camera/motion if video; for a website, app or game: purpose, audience, features, screens or levels, visual style).
**Negative prompt:** things to avoid (only for image/video).
**Key details:** 3-5 short bullets on what drove the prompt.

For documents or text/code, the prompt is the instruction that would generate that content.
For audio, work from the transcript. Describe only what is visible or present; do not invent details."""

PAGE_INSTRUCTION = (
    "This is a web page for a website, app, game or video. Using the details below (and the preview image if "
    "one is provided), write the prompt that would let an AI builder recreate it: purpose, audience, core "
    "features, screens or levels, visual style and tone. If it is a video or media page, write the prompt "
    "for the content it describes. Use only what the details support."
)
AUDIO_INSTRUCTION = (
    "This is the transcript of an audio file. Write the prompt that would recreate it: the script or "
    "message, the likely speaker style, pacing and format (for example a voiceover, podcast or call)."
)

app = FastAPI(title="Prompt from File")

# What prepare() returns: instruction, images [(bytes, mime)], text, notes shown to the user
Prepared = tuple[str, list[tuple[bytes, str]], str | None, list[str]]


def video_frames(data: bytes, suffix: str) -> list[bytes]:
    if not (shutil.which("ffmpeg") and shutil.which("ffprobe")):
        raise HTTPException(500, "ffmpeg and ffprobe are required for video. Install them and retry.")
    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp) / f"in{suffix or '.mp4'}"
        src.write_bytes(data)
        probe = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=nw=1:nk=1", str(src)],
            capture_output=True, text=True, timeout=30,
        )
        try:
            duration = float(probe.stdout.strip())
        except ValueError:
            raise HTTPException(400, "Could not read this video.") from None
        fps = VIDEO_FRAMES / max(duration, 0.1)
        subprocess.run(
            ["ffmpeg", "-v", "error", "-i", str(src), "-vf",
             f"fps={fps:.4f},scale='min(768,iw)':-2", "-frames:v", str(VIDEO_FRAMES),
             str(Path(tmp) / "f_%02d.jpg")],
            check=False, timeout=120,
        )
        frames = sorted(Path(tmp).glob("f_*.jpg"))
        if not frames:
            raise HTTPException(400, "No frames could be extracted from this video.")
        return [f.read_bytes() for f in frames]


def pdf_text(data: bytes) -> str:
    try:
        from pypdf import PdfReader
    except ImportError:
        raise HTTPException(500, "pypdf is required for PDFs: pip install pypdf") from None
    reader = PdfReader(io.BytesIO(data))
    return "\n".join((p.extract_text() or "") for p in reader.pages)[:100_000]


def prepare(name: str, mime: str, data: bytes, allow_cloud: bool = False) -> Prepared:
    ext = Path(name).suffix.lower()
    if mime in IMAGE_TYPES:
        return "Write the prompt that would recreate this image.", [(data, mime)], None, []
    if mime.startswith("video/"):
        frames = [(f, "image/jpeg") for f in video_frames(data, ext)]
        return (
            "These are evenly spaced frames from one video. Write the prompt that would "
            "recreate the whole video, including motion and camera work.",
            frames, None, ["Only sampled frames are analyzed. The audio track is not."],
        )
    if mime.startswith("audio/") or ext in AUDIO_EXTS:
        transcript = transcribe(name, mime, data, allow_cloud).strip()
        if not transcript:
            raise HTTPException(
                422, "No speech was found in this audio. Music and sound effects can't be analyzed yet."
            )
        return (AUDIO_INSTRUCTION, [], f"Transcript:\n{transcript[:100_000]}",
                ["Only speech is transcribed. Music, tone of voice and sound effects are not analyzed."])
    if mime == "application/pdf":
        return "Write the prompt that would generate this document.", [], pdf_text(data), []
    if mime.startswith("text/") or ext in TEXT_EXTS:
        return ("Write the prompt that would generate this content.", [],
                data.decode("utf-8", errors="replace")[:100_000], [])
    raise HTTPException(415, f"Unsupported file type: {mime or ext}. Try an image, video, audio, PDF or text file.")


def prepare_page(url: str, html: bytes) -> Prepared:
    page = extract_page(html)
    if not (page["title"] or page["description"] or len(page["text"]) > 50):
        raise HTTPException(422, "Nothing could be read from this page. It may need JavaScript or a login.")
    notes = ["Based on the page's title, description, text and preview image. "
             "Videos, apps and games themselves are not opened or played."]
    images: list[tuple[bytes, str]] = []
    if page["image"]:
        try:
            _, ctype, img = fetch(urljoin(url, page["image"]), PREVIEW_IMAGE_BYTES)
            if ctype in IMAGE_TYPES:
                images.append((img, ctype))
        except HTTPException:
            notes.append("The preview image could not be loaded.")
    if len(page["text"]) < 200 and not page["description"]:
        notes.append("This page builds its content with JavaScript, so very little could be read.")
    return PAGE_INSTRUCTION, images, describe(page, url), notes


def prepare_url(url: str, allow_cloud: bool) -> tuple[str, str, Prepared]:
    """Fetch a link and prepare it. Returns (final_url, content_type, prepared)."""
    final_url, ctype, data = fetch(url, MAX_BYTES)
    if not data:
        raise HTTPException(400, "The link returned an empty file.")
    if ctype in HTML_TYPES or not ctype:
        return final_url, ctype or "text/html", prepare_page(final_url, data)
    name = Path(urlsplit(final_url).path).name or "download"
    return final_url, ctype, prepare(name, ctype, data, allow_cloud)


def run_ollama(instruction: str, images: list[tuple[bytes, str]], text: str | None) -> str:
    content = instruction + (f"\n\n{text}" if text else "")
    msg = {"role": "user", "content": content}
    if images:
        msg["images"] = [base64.b64encode(b).decode() for b, _ in images]
    try:
        r = httpx.post(
            f"{OLLAMA_URL}/api/chat",
            json={"model": OLLAMA_MODEL, "stream": False,
                  "messages": [{"role": "system", "content": SYSTEM}, msg]},
            timeout=600,
        )
    except httpx.ConnectError:
        raise HTTPException(502, f"Can't reach Ollama at {OLLAMA_URL}. Is it running? (ollama serve)") from None
    if r.status_code != 200:
        raise HTTPException(502, f"Ollama error: {r.text[:300]}")
    return r.json()["message"]["content"]


def run_openai(instruction: str, images: list[tuple[bytes, str]], text: str | None) -> str:
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        raise HTTPException(502, "OPENAI_API_KEY is not set.")
    parts = [{"type": "text", "text": instruction + (f"\n\n{text}" if text else "")}]
    for b, m in images:
        parts.append({"type": "image_url",
                      "image_url": {"url": f"data:{m};base64,{base64.b64encode(b).decode()}"}})
    try:
        r = httpx.post(
            OPENAI_URL,
            headers={"Authorization": f"Bearer {key}"},
            json={"model": OPENAI_MODEL, "max_tokens": 1500,
                  "messages": [{"role": "system", "content": SYSTEM},
                               {"role": "user", "content": parts}]},
            timeout=120,
        )
    except httpx.HTTPError as e:
        raise HTTPException(502, f"Can't reach OpenAI: {e}") from None
    if r.status_code != 200:
        raise HTTPException(502, f"OpenAI error: {r.text[:300]}")
    return r.json()["choices"][0]["message"]["content"]


def run_claude(instruction: str, images: list[tuple[bytes, str]], text: str | None) -> str:
    key = os.getenv("ANTHROPIC_API_KEY")
    if not key:
        raise HTTPException(502, "ANTHROPIC_API_KEY is not set.")
    blocks = []
    for b, m in images:
        blocks.append({"type": "image", "source": {"type": "base64", "media_type": m,
                                                     "data": base64.b64encode(b).decode()}})
    blocks.append({"type": "text", "text": instruction + (f"\n\n{text}" if text else "")})
    try:
        r = httpx.post(
            CLAUDE_URL,
            headers={"x-api-key": key, "anthropic-version": "2023-06-01"},
            json={"model": CLAUDE_MODEL, "max_tokens": 1500, "system": SYSTEM,
                  "messages": [{"role": "user", "content": blocks}]},
            timeout=120,
        )
    except httpx.HTTPError as e:
        raise HTTPException(502, f"Can't reach Claude: {e}") from None
    if r.status_code != 200:
        raise HTTPException(502, f"Claude error: {r.text[:300]}")
    return "".join(b.get("text", "") for b in r.json()["content"] if b.get("type") == "text")


RUNNERS = {"ollama": run_ollama, "openai": run_openai, "claude": run_claude}
FALLBACK_KEYS = [("openai", "OPENAI_API_KEY"), ("claude", "ANTHROPIC_API_KEY")]


def _handle(name: str, mime: str, data: bytes | None, url: str, note: str, provider: str) -> dict:
    choice = (provider or PROVIDER).lower()
    if choice != "auto" and choice not in RUNNERS:
        raise HTTPException(400, "provider must be auto, ollama, openai or claude.")
    # Cloud transcription sends audio off the machine, so only do it when ChatGPT was chosen on purpose.
    allow_cloud = choice == "openai" or os.getenv("ALLOW_CLOUD_TRANSCRIPTION") == "1"
    try:
        if url:
            source = url
            _, mime, prepared = prepare_url(url, allow_cloud)
        else:
            source = name
            prepared = prepare(name, mime, data or b"", allow_cloud)
    except subprocess.TimeoutExpired:
        raise HTTPException(400, "Video processing timed out. Try a shorter or smaller video.") from None
    instruction, images, text, notes = prepared
    if note.strip():
        instruction += f"\nExtra context from the user: {note.strip()}"

    if choice == "auto":  # local first, then ChatGPT, then Claude (whichever keys are set)
        chain = ["ollama"] + [n for n, env in FALLBACK_KEYS if os.getenv(env)]
    else:
        chain = [choice]
    last_error: HTTPException | None = None
    for used in chain:
        try:
            result = RUNNERS[used](instruction, images, text)
            break
        except HTTPException as e:
            last_error = e
        except (KeyError, IndexError, TypeError, ValueError):
            last_error = HTTPException(502, f"{used} returned an unexpected response.")
    else:
        raise last_error
    return {"source": source, "type": mime, "provider": used, "notes": notes, "prompt": result}


@app.post("/api/prompt")
async def make_prompt(
    file: UploadFile | None = File(None),
    url: str = Form(""),
    note: str = Form(""),
    provider: str = Form(""),
):
    url = url.strip()
    if bool(file) == bool(url):
        raise HTTPException(400, "Send either a file or a link, not both and not neither.")
    name, mime, data = "", "", None
    if file:
        data = await file.read(MAX_BYTES + 1)  # never buffer more than the limit
        if len(data) > MAX_BYTES:
            raise HTTPException(413, f"File too large (max {MAX_BYTES // 1024 // 1024} MB).")
        if not data:
            raise HTTPException(400, "Empty file.")
        name, mime = file.filename or "upload", file.content_type or ""
    # Blocking work (downloads, ffmpeg, model calls) runs off the event loop.
    return await run_in_threadpool(_handle, name, mime, data, url, note, provider)


app.mount("/static", StaticFiles(directory=Path(__file__).parent / "static"), name="static")


@app.get("/")
def index():
    return FileResponse(Path(__file__).parent / "static" / "index.html")
