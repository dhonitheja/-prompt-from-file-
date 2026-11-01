"""Tests for the upload -> prompt API. All model backends are mocked."""
import io
import sys
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import app as appmod  # noqa: E402

PNG = (b"\x89PNG\r\n\x1a\n" + b"0" * 32)
TXT = ("a.txt", b"hello", "text/plain")


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    for k in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY"):
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setattr(appmod, "PROVIDER", "auto")


@pytest.fixture
def client():
    return TestClient(appmod.app)


@pytest.fixture
def backends(monkeypatch):
    """Mock all three backends. Set .ollama_up = False to simulate Ollama down."""
    calls = []

    class State:
        ollama_up = True
        ollama_body = {"message": {"content": "LOCAL"}}

    def fake_post(url, **kw):
        calls.append((url, kw))
        if "11434" in url:
            if not State.ollama_up:
                raise httpx.ConnectError("down")
            return httpx.Response(200, json=State.ollama_body)
        if "openai" in url:
            return httpx.Response(200, json={"choices": [{"message": {"content": "GPT"}}]})
        if "anthropic" in url:
            return httpx.Response(200, json={"content": [{"type": "text", "text": "CLAUDE"}]})
        raise AssertionError(url)

    monkeypatch.setattr(appmod.httpx, "post", fake_post)
    State.calls = calls
    return State


def post(client, file=TXT, **data):
    return client.post("/api/prompt", files={"file": file}, data=data)


def test_index_served(client):
    assert client.get("/").status_code == 200


def test_local_default(client, backends):
    r = post(client)
    assert r.status_code == 200
    assert r.json()["provider"] == "ollama"
    assert r.json()["prompt"] == "LOCAL"


def test_image_is_sent_to_vision_model(client, backends):
    post(client, ("p.png", PNG, "image/png"))
    payload = backends.calls[0][1]["json"]
    assert payload["messages"][1]["images"]


def test_unsupported_type_415(client, backends):
    assert post(client, ("a.bin", b"x", "application/octet-stream")).status_code == 415


def test_empty_file_400(client, backends):
    assert post(client, ("a.txt", b"", "text/plain")).status_code == 400


def test_too_large_413(client, backends, monkeypatch):
    monkeypatch.setattr(appmod, "MAX_BYTES", 10)
    assert post(client, ("a.txt", b"x" * 100, "text/plain")).status_code == 413


def test_bad_provider_400(client, backends):
    assert post(client, provider="bogus").status_code == 400


def test_ollama_down_no_keys_returns_502(client, backends):
    backends.ollama_up = False
    r = post(client)
    assert r.status_code == 502 and "Ollama" in r.json()["detail"]


def test_auto_falls_back_to_chatgpt(client, backends, monkeypatch):
    backends.ollama_up = False
    monkeypatch.setenv("OPENAI_API_KEY", "k")
    r = post(client)
    assert r.json()["provider"] == "openai" and r.json()["prompt"] == "GPT"


def test_auto_falls_back_to_claude_when_only_claude_key(client, backends, monkeypatch):
    backends.ollama_up = False
    monkeypatch.setenv("ANTHROPIC_API_KEY", "k")
    r = post(client)
    assert r.json()["provider"] == "claude" and r.json()["prompt"] == "CLAUDE"


def test_explicit_claude_sends_key_header(client, backends, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "secret")
    post(client, provider="claude")
    assert backends.calls[0][1]["headers"]["x-api-key"] == "secret"


def test_explicit_cloud_without_key_502(client, backends):
    assert post(client, provider="openai").status_code == 502
    assert post(client, provider="claude").status_code == 502


def test_explicit_ollama_does_not_fall_back(client, backends, monkeypatch):
    backends.ollama_up = False
    monkeypatch.setenv("OPENAI_API_KEY", "k")
    assert post(client, provider="ollama").status_code == 502


def test_malformed_model_response_is_502_not_500(client, backends):
    backends.ollama_body = {"unexpected": True}
    r = post(client)
    assert r.status_code == 502


def test_note_is_forwarded(client, backends):
    post(client, note="for Midjourney")
    assert "for Midjourney" in backends.calls[0][1]["json"]["messages"][1]["content"]


def test_pdf_text_extracted(client, backends):
    from pypdf import PdfWriter
    buf = io.BytesIO()
    w = PdfWriter()
    w.add_blank_page(width=72, height=72)
    w.write(buf)
    r = post(client, ("a.pdf", buf.getvalue(), "application/pdf"))
    assert r.status_code == 200
