"""Tests for the shared-password login, hosted-mode safety check and security headers."""
import base64

import pytest

import app as appmod

PASSWORD = "correct-horse-battery"
TXT = ("a.txt", b"hello", "text/plain")


def test_open_when_no_password_set(client):
    assert client.get("/").status_code == 200


def test_security_headers_always_present(client):
    h = client.get("/").headers
    assert h["x-content-type-options"] == "nosniff"
    assert h["x-frame-options"] == "DENY"
    assert "frame-ancestors 'none'" in h["content-security-policy"]


@pytest.fixture
def locked(monkeypatch):
    monkeypatch.setenv("APP_PASSWORD", PASSWORD)


@pytest.mark.parametrize("path", ["/", "/static/index.html", "/docs", "/openapi.json"])
def test_pages_require_password(client, locked, path):
    r = client.get(path)
    assert r.status_code == 401
    assert r.headers["www-authenticate"].startswith("Basic")
    assert "content-security-policy" in r.headers  # headers are added to the 401 too


def test_api_requires_password(client, backends, locked):
    assert client.post("/api/prompt", files={"file": TXT}).status_code == 401
    assert not backends.calls  # no model was called


def test_correct_password_any_username(client, backends, locked):
    assert client.get("/", auth=("anyone", PASSWORD)).status_code == 200
    r = client.post("/api/prompt", files={"file": TXT}, auth=("", PASSWORD))
    assert r.status_code == 200


@pytest.mark.parametrize("header", [
    "Basic " + base64.b64encode(b"u:wrong").decode(),
    "Basic " + base64.b64encode(b"u:").decode(),
    "Basic " + base64.b64encode(f"u:{PASSWORD}x".encode()).decode(),
    "Basic !!!not-base64!!!",
    "Basic " + base64.b64encode(b"\xff\xfe:\xff").decode(),
    "Bearer " + PASSWORD,
    "Basic",
    "",
])
def test_wrong_credentials_rejected(client, locked, header):
    assert client.get("/", headers={"Authorization": header}).status_code == 401


def test_healthz_is_open(client, locked):
    r = client.get("/healthz")
    assert r.status_code == 200 and r.json() == {"ok": True}


def test_hosted_mode_requires_strong_password(monkeypatch):
    monkeypatch.setenv("HOSTED", "1")
    monkeypatch.delenv("APP_PASSWORD", raising=False)
    with pytest.raises(RuntimeError):
        appmod.check_config()
    monkeypatch.setenv("APP_PASSWORD", "short")
    with pytest.raises(RuntimeError):
        appmod.check_config()
    monkeypatch.setenv("APP_PASSWORD", "long-enough-pw")
    appmod.check_config()  # no error


def test_local_mode_needs_no_password(monkeypatch):
    monkeypatch.delenv("HOSTED", raising=False)
    monkeypatch.delenv("APP_PASSWORD", raising=False)
    appmod.check_config()
