"""Tests for link input, including protection against requests to private networks."""
import httpx
import pytest

import app as appmod
import sources

PUBLIC_IP = "93.184.216.34"
PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 32

PAGE = b"""<html><head>
<title>Space Raiders</title>
<meta property="og:title" content="Space Raiders - Arcade Shooter">
<meta property="og:description" content="Dodge asteroids and fight bosses across 12 levels.">
<meta property="og:image" content="/cover.png">
</head><body><script>var x=1;</script><h1>Space Raiders</h1><p>Pilot your ship through neon space.</p></body></html>"""


def respond(body=b"", ctype="text/html", status=200, **headers):
    return lambda: httpx.Response(status, content=body, headers={"content-type": ctype, **headers})


class Routes(dict):
    """Maps (host, path) to a response factory, and records every request that was made."""

    def __init__(self):
        super().__init__()
        self.seen = []


@pytest.fixture
def web(monkeypatch):
    """Fake internet. Hosts ending in .test resolve to a public IP."""
    routes = Routes()
    seen = routes.seen
    real_resolve = sources._resolve

    def handler(request):
        # The connection must be pinned to the address we validated, with the real name in Host and SNI.
        assert request.url.host == PUBLIC_IP
        seen.append(request)
        route = routes.get((request.headers["host"], request.url.path))
        return route() if route else httpx.Response(404)

    monkeypatch.setattr(sources, "_resolve", lambda h: [PUBLIC_IP] if h.endswith(".test") else real_resolve(h))
    monkeypatch.setattr(sources, "_transport", httpx.MockTransport(handler))
    return routes


def link(client, url, **data):
    return client.post("/api/prompt", data={"url": url, **data})


def test_web_page_link(client, backends, web):
    web[("game.test", "/")] = respond(PAGE)
    web[("game.test", "/cover.png")] = respond(PNG, "image/png")
    r = link(client, "https://game.test/")
    assert r.status_code == 200
    msg = backends.calls[0][1]["json"]["messages"][1]
    assert "Space Raiders - Arcade Shooter" in msg["content"]
    assert "Dodge asteroids" in msg["content"]
    assert "neon space" in msg["content"]
    assert "var x" not in msg["content"]  # scripts are not page text
    assert len(msg["images"]) == 1  # the preview image
    assert any("not opened or played" in n for n in r.json()["notes"])
    assert web.seen[0].extensions["sni_hostname"] == "game.test"


def test_direct_image_link(client, backends, web):
    web[("img.test", "/cat.png")] = respond(PNG, "image/png")
    r = link(client, "https://img.test/cat.png")
    assert r.status_code == 200
    assert backends.calls[0][1]["json"]["messages"][1]["images"]


def test_missing_preview_image_is_a_note_not_an_error(client, backends, web):
    web[("game.test", "/")] = respond(PAGE)  # /cover.png is a 404
    r = link(client, "https://game.test/")
    assert r.status_code == 200
    assert any("preview image" in n for n in r.json()["notes"])


@pytest.mark.parametrize("url", [
    "http://localhost/",
    "http://127.0.0.1/",
    "http://169.254.169.254/latest/meta-data/",
    "http://10.0.0.5/",
    "http://192.168.1.1/",
    "http://[::1]/",
    "http://[::ffff:127.0.0.1]/",
    "http://2130706433/",
    "http://0.0.0.0/",
    "ftp://game.test/file",
    "file:///etc/passwd",
    "javascript:alert(1)",
    "https://game.test:8080/",
    "not a url",
])
def test_unsafe_links_rejected(client, backends, web, url):
    assert link(client, url).status_code == 400
    assert not web.seen  # nothing was ever requested


def test_hostname_resolving_to_private_address_rejected(client, backends, web, monkeypatch):
    real = sources._resolve
    monkeypatch.setattr(sources, "_resolve", lambda h: ["10.0.0.1"] if h == "evil.test" else real(h))
    assert link(client, "https://evil.test/").status_code == 400
    assert not web.seen


def test_host_with_one_private_address_rejected(client, backends, web, monkeypatch):
    real = sources._resolve
    monkeypatch.setattr(sources, "_resolve", lambda h: [PUBLIC_IP, "127.0.0.1"] if h == "mixed.test" else real(h))
    assert link(client, "https://mixed.test/").status_code == 400


def test_redirect_to_private_address_rejected(client, backends, web):
    web[("game.test", "/")] = respond(status=302, location="http://169.254.169.254/latest/meta-data/")
    assert link(client, "https://game.test/").status_code == 400
    assert len(web.seen) == 1  # the redirect target was never contacted


def test_redirect_is_followed(client, backends, web):
    web[("game.test", "/")] = respond(status=301, location="/final")
    web[("game.test", "/final")] = respond(PAGE)
    assert link(client, "https://game.test/").status_code == 200


def test_redirect_loop_rejected(client, backends, web):
    web[("game.test", "/")] = respond(status=302, location="/")
    assert link(client, "https://game.test/").status_code == 400


def test_http_error_status_400(client, backends, web):
    assert link(client, "https://game.test/missing").status_code == 400


def test_link_too_large_413(client, backends, web, monkeypatch):
    monkeypatch.setattr(appmod, "MAX_BYTES", 50)
    web[("game.test", "/")] = respond(PAGE)
    assert link(client, "https://game.test/").status_code == 413


def test_page_with_no_content_422(client, backends, web):
    web[("app.test", "/")] = respond(b"<html><body><div id='root'></div><script>x</script></body></html>")
    assert link(client, "https://app.test/").status_code == 422


def test_link_with_provider_choice(client, backends, web, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "k")
    web[("game.test", "/")] = respond(PAGE)
    r = link(client, "https://game.test/", provider="claude")
    assert r.json()["provider"] == "claude"


def test_audio_link(client, backends, web, monkeypatch):
    class Fake:
        def transcribe(self, path):
            return [type("S", (), {"text": "spoken words"})()], None

    monkeypatch.setattr("audio._load_local", lambda: Fake())
    web[("pod.test", "/ep1.mp3")] = respond(b"audio-bytes", "audio/mpeg")
    r = link(client, "https://pod.test/ep1.mp3")
    assert r.status_code == 200
    assert "spoken words" in backends.calls[0][1]["json"]["messages"][1]["content"]
