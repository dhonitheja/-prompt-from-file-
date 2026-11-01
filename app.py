"""Upload a file (image, video, PDF, text) and get back a reverse-engineered prompt.

Runs on a local model via Ollama by default. Set LLM_PROVIDER=claude to use the Claude API.
"""
import base64
import io
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

import httpx
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

PROVIDER = os.getenv("LLM_PROVIDER", "ollama").lower()  # "ollama" or "claude"
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2-vision")  # any vision model: qwen2.5vl, llava, gemma3...
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-sonnet-5-5")
MAX_BYTES = int(os.getenv("MAX_UPLOAD_MB", "50")) * 1024 * 1024
VIDEO_FRAMES = int(os.getenv("VIDEO_FRAMES", "6"))

IMAGE_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"}
TEXT_EXTS = {".txt", ".md", ".csv", ".json", ".py", ".js", ".ts", ".html", ".css", ".xml", ".yaml", ".yml", ".log"}

SYSTEM = """You reverse-engineer prompts. Given an uploaded file (or frames from a video),
write the prompt someone could give a generative AI tool to recreate it.

Respond in this format:
**Prompt:** one polished, ready-to-paste prompt (subject, style, composition, lighting, color, mood, camera/motion if video).
**Negative prompt:** things to avoid (only for image/video).
**Key details:** 3-5 short bullets on what drove the prompt.

For documents or text/code, the prompt is the instruction that would generate that content.
Describe only what is visible or present; do not invent details."""

app = FastAPI(title="Prompt from File")


def video_frames(data: bytes, suffix: str) -> list[bytes]:
    if not shutil.which("ffmpeg"):
        raise HTTPException(500, "ffmpeg is required for video. Install it and retry.")
    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp) / f"in{suffix or '.mp4'}"
        src.write_bytes(data)
        probe = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=nw=1:nk=1", str(src)],
            capture_output=True, text=True,
        )
        try:
            duration = float(probe.stdout.strip())
        except ValueError:
            raise HTTPException(400, "Could not read this video.")
        fps = VIDEO_FRAMES / max(duration, 0.1)
        subprocess.run(
            ["ffmpeg", "-v", "error", "-i", str(src), "-vf",
             f"fps={fps:.4f},scale='min(768,iw)':-2", "-frames:v", str(VIDEO_FRAMES),
             str(Path(tmp) / "f_%02d.jpg")],
            check=False,
        )
        frames = sorted(Path(tmp).glob("f_*.jpg"))
        if not frames:
            raise HTTPException(400, "No frames could be extracted from this video.")
        return [f.read_bytes() for f in frames]


def pdf_text(data: bytes) -> str:
    try:
        from pypdf import PdfReader
    except ImportError:
        raise HTTPException(500, "pypdf is required for PDFs: pip install pypdf")
    reader = PdfReader(io.BytesIO(data))
    return "\n".join((p.extract_text() or "") for p in reader.pages)[:100_000]


def prepare(name: str, mime: str, data: bytes) -> tuple[str, list[tuple[bytes, str]], str | None]:
    """Return (instruction, images[(bytes, mime)], text). Provider-neutral."""
    ext = Path(name).suffix.lower()
    if mime in IMAGE_TYPES:
        return "Write the prompt that would recreate this image.", [(data, mime)], None
    if mime.startswith("video/"):
        frames = [(f, "image/jpeg") for f in video_frames(data, ext)]
        return ("These are evenly spaced frames from one video. Write the prompt that would "
                "recreate the whole video, including motion and camera work."), frames, None
    if mime == "application/pdf":
        return "Write the prompt that would generate this document.", [], pdf_text(data)
    if mime.startswith("text/") or ext in TEXT_EXTS:
        return ("Write the prompt that would generate this content.", [],
                data.decode("utf-8", errors="replace")[:100_000])
    raise HTTPException(415, f"Unsupported file type: {mime or ext}. Try image, video, PDF or text.")


def run_ollama(instruction: str, images: list[tuple[bytes, str]], text: str | None) -> str:
    content = instruction + (f"\n\nFile content:\n{text}" if text else "")
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
        raise HTTPException(502, f"Can't reach Ollama at {OLLAMA_URL}. Is it running? (ollama serve)")
    if r.status_code != 200:
        raise HTTPException(502, f"Ollama error: {r.text[:300]}")
    return r.json()["message"]["content"]


def run_claude(instruction: str, images: list[tuple[bytes, str]], text: str | None) -> str:
    import anthropic
    blocks = []
    for b, m in images:
        blocks.append({"type": "image", "source": {"type": "base64", "media_type": m,
                                                     "data": base64.b64encode(b).decode()}})
    if text:
        blocks.append({"type": "text", "text": f"File content:\n{text}"})
    blocks.append({"type": "text", "text": instruction})
    try:
        resp = anthropic.Anthropic().messages.create(
            model=CLAUDE_MODEL, max_tokens=1500, system=SYSTEM,
            messages=[{"role": "user", "content": blocks}],
        )
    except anthropic.APIError as e:
        raise HTTPException(502, f"Claude API error: {e}")
    return "".join(b.text for b in resp.content if b.type == "text")


@app.post("/api/prompt")
async def make_prompt(file: UploadFile = File(...), note: str = Form("")):
    data = await file.read()
    if len(data) > MAX_BYTES:
        raise HTTPException(413, f"File too large (max {MAX_BYTES // 1024 // 1024} MB).")
    if not data:
        raise HTTPException(400, "Empty file.")
    mime = file.content_type or ""
    instruction, images, text = prepare(file.filename or "upload", mime, data)
    if note.strip():
        instruction += f"\nExtra context from the user: {note.strip()}"
    run = run_claude if PROVIDER == "claude" else run_ollama
    return {"filename": file.filename, "type": mime, "provider": PROVIDER,
            "prompt": run(instruction, images, text)}


app.mount("/static", StaticFiles(directory=Path(__file__).parent / "static"), name="static")


@app.get("/")
def index():
    return FileResponse(Path(__file__).parent / "static" / "index.html")
