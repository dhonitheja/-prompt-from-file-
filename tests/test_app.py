"""Tests for file uploads and provider selection."""
import io

import app as appmod

PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 32
TXT = ("a.txt", b"hello", "text/plain")


def post(client, file=TXT, **data):
    return client.post("/api/prompt", files={"file": file}, data=data)


def test_index_served(client):
    assert client.get("/").status_code == 200


def test_local_default(client, backends):
    r = post(client)
    assert r.status_code == 200
    assert r.json()["provider"] == "ollama"
    assert r.json()["prompt"] == "LOCAL"
    assert r.json()["source"] == "a.txt"


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


def test_neither_file_nor_link_400(client, backends):
    assert client.post("/api/prompt", data={}).status_code == 400


def test_both_file_and_link_400(client, backends):
    r = client.post("/api/prompt", files={"file": TXT}, data={"url": "https://game.test/"})
    assert r.status_code == 400


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
    assert post(client).status_code == 502


def test_note_is_forwarded(client, backends):
    post(client, note="for Midjourney")
    assert "for Midjourney" in backends.calls[0][1]["json"]["messages"][1]["content"]


def test_pdf_text_extracted(client, backends):
    from pypdf import PdfWriter
    buf = io.BytesIO()
    w = PdfWriter()
    w.add_blank_page(width=72, height=72)
    w.write(buf)
    assert post(client, ("a.pdf", buf.getvalue(), "application/pdf")).status_code == 200


# --- audio ---

MP3 = ("talk.mp3", b"fake-audio", "audio/mpeg")


class _Seg:
    def __init__(self, text):
        self.text = text


class _FakeWhisper:
    def __init__(self, words):
        self.words = words

    def transcribe(self, path):
        return [_Seg(w) for w in self.words], None


def test_audio_transcribed_locally(client, backends, monkeypatch):
    monkeypatch.setattr("audio._load_local", lambda: _FakeWhisper(["Welcome", "to the show"]))
    r = post(client, MP3)
    assert r.status_code == 200
    assert "Welcome to the show" in backends.calls[0][1]["json"]["messages"][1]["content"]
    assert any("speech" in n for n in r.json()["notes"])


def test_audio_without_speech_422(client, backends, monkeypatch):
    monkeypatch.setattr("audio._load_local", lambda: _FakeWhisper([]))
    assert post(client, MP3).status_code == 422


def test_audio_without_backend_501(client, backends):
    assert post(client, MP3).status_code == 501


def test_audio_not_sent_to_cloud_unless_chatgpt_chosen(client, backends, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "k")
    assert post(client, MP3).status_code == 501  # auto: key is set but audio stays local
    assert post(client, MP3, provider="ollama").status_code == 501
    assert not any("transcriptions" in url for url, _ in backends.calls)


def test_audio_cloud_transcription_when_chatgpt_chosen(client, backends, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "k")
    r = post(client, MP3, provider="openai")
    assert r.status_code == 200
    assert any("transcriptions" in url for url, _ in backends.calls)
