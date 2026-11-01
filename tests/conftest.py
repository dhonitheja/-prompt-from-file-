"""Shared fixtures. Every model and network call is mocked."""
import sys
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import app as appmod  # noqa: E402


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    for k in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "ALLOW_CLOUD_TRANSCRIPTION"):
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setattr(appmod, "PROVIDER", "auto")
    # Never load a real Whisper model in tests.
    monkeypatch.setattr("audio._load_local", lambda: None)


@pytest.fixture
def client():
    return TestClient(appmod.app)


@pytest.fixture
def backends(monkeypatch):
    """Mock Ollama, OpenAI chat, OpenAI transcription and Anthropic. Set .ollama_up = False to simulate Ollama down."""
    calls = []

    class State:
        ollama_up = True
        ollama_body = None

    State.calls = calls
    State.ollama_body = {"message": {"content": "LOCAL"}}

    def fake_post(url, **kw):
        calls.append((url, kw))
        if "11434" in url:
            if not State.ollama_up:
                raise httpx.ConnectError("down")
            return httpx.Response(200, json=State.ollama_body)
        if "audio/transcriptions" in url:
            return httpx.Response(200, json={"text": "hello from the cloud"})
        if "openai" in url:
            return httpx.Response(200, json={"choices": [{"message": {"content": "GPT"}}]})
        if "anthropic" in url:
            return httpx.Response(200, json={"content": [{"type": "text", "text": "CLAUDE"}]})
        raise AssertionError(url)

    monkeypatch.setattr(appmod.httpx, "post", fake_post)
    return State
