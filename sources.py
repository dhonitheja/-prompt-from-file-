"""Fetch user-supplied links safely and read what a web page says about itself.

Fetching a URL the user typed is a classic SSRF risk (someone asks the server to open
http://localhost:11434 or a cloud metadata address). So every hop is checked:
only http/https on ports 80/443, the host must resolve to public addresses only, the
connection is pinned to the address we checked, redirects are followed by hand and
re-checked, and the download is capped in size and time.
"""
import ipaddress
import socket
import time
from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit

import httpx
from fastapi import HTTPException

MAX_REDIRECTS = 5
TOTAL_TIMEOUT = 20  # seconds for one fetch, including redirects
USER_AGENT = "Mozilla/5.0 (compatible; PromptFromFile/1.0)"
HTML_TYPES = {"text/html", "application/xhtml+xml"}

_transport: httpx.BaseTransport | None = None  # tests inject an httpx.MockTransport


def _resolve(host: str) -> list[str]:
    try:
        infos = socket.getaddrinfo(host, None, type=socket.SOCK_STREAM)
    except (socket.gaierror, UnicodeError):
        raise HTTPException(400, f"Could not find the site {host}.") from None
    return sorted({i[4][0] for i in infos}, key=lambda ip: ":" in ip)  # IPv4 first


def _is_public(ip: str) -> bool:
    addr = ipaddress.ip_address(ip.split("%")[0])
    mapped = getattr(addr, "ipv4_mapped", None)
    return (mapped or addr).is_global


def check_public(host: str) -> str:
    """Return one address for host, or raise unless every address it resolves to is public."""
    ips = _resolve(host)
    if not ips or not all(_is_public(ip) for ip in ips):
        raise HTTPException(400, "That link points to a private or local address, which is not allowed.")
    return ips[0]


def fetch(url: str, max_bytes: int) -> tuple[str, str, bytes]:
    """Download url. Returns (final_url, content_type, body)."""
    deadline = time.monotonic() + TOTAL_TIMEOUT
    for _ in range(MAX_REDIRECTS + 1):
        parts = urlsplit(url)
        try:
            port = parts.port
        except ValueError:
            raise HTTPException(400, "That link is not valid.") from None
        if parts.scheme not in ("http", "https") or not parts.hostname:
            raise HTTPException(400, "Only http and https links are supported.")
        if port not in (None, 80, 443):
            raise HTTPException(400, "Only ports 80 and 443 are allowed.")
        host = parts.hostname
        ip = check_public(host)
        shown = f"[{host}]" if ":" in host else host
        pinned = parts._replace(netloc=f"[{ip}]" if ":" in ip else ip)
        if port:
            pinned = pinned._replace(netloc=f"{pinned.netloc}:{port}")
        headers = {"Host": shown + (f":{port}" if port else ""), "User-Agent": USER_AGENT, "Accept": "*/*"}
        try:
            with httpx.Client(transport=_transport, timeout=10, follow_redirects=False) as client, \
                    client.stream("GET", pinned.geturl(), headers=headers,
                                  extensions={"sni_hostname": host}) as r:
                if r.status_code in (301, 302, 303, 307, 308):
                    location = r.headers.get("location")
                    if not location:
                        raise HTTPException(400, "The link redirected without saying where.")
                    url = urljoin(url, location)
                    continue
                if r.status_code != 200:
                    raise HTTPException(400, f"The link returned HTTP {r.status_code}.")
                if int(r.headers.get("content-length") or 0) > max_bytes:
                    raise HTTPException(413, "The linked file is too large.")
                body = bytearray()
                for chunk in r.iter_bytes():
                    body += chunk
                    if len(body) > max_bytes:
                        raise HTTPException(413, "The linked file is too large.")
                    if time.monotonic() > deadline:
                        raise HTTPException(504, "The link took too long to download.")
                ctype = r.headers.get("content-type", "").split(";")[0].strip().lower()
                return url, ctype, bytes(body)
        except httpx.HTTPError as e:
            raise HTTPException(502, f"Could not open the link: {e.__class__.__name__}") from None
    raise HTTPException(400, "The link redirected too many times.")


class _PageParser(HTMLParser):
    SKIP = {"script", "style", "noscript", "svg", "template", "head"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.meta: dict[str, str] = {}
        self.title = ""
        self.text: list[str] = []
        self._skip = 0
        self._in_title = False

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "meta":
            key = (a.get("property") or a.get("name") or "").lower()
            if key and a.get("content"):
                self.meta.setdefault(key, a["content"].strip())
        elif tag == "title":
            self._in_title = True
        elif tag in self.SKIP:
            self._skip += 1

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False
        elif tag in self.SKIP and self._skip:
            self._skip -= 1

    def handle_data(self, data):
        if self._in_title:
            self.title += data
        elif not self._skip and data.strip():
            self.text.append(data.strip())


def extract_page(html: bytes) -> dict[str, str]:
    """Pull the title, description, preview image and visible text out of an HTML page."""
    p = _PageParser()
    p.feed(html.decode("utf-8", errors="replace"))
    m = p.meta
    return {
        "title": (m.get("og:title") or m.get("twitter:title") or p.title).strip(),
        "site": m.get("og:site_name", ""),
        "type": m.get("og:type", ""),
        "description": m.get("og:description") or m.get("twitter:description") or m.get("description", ""),
        "image": m.get("og:image") or m.get("twitter:image", ""),
        "text": " ".join(p.text)[:6000],
    }


def describe(page: dict[str, str], url: str) -> str:
    lines = [f"URL: {url}"]
    for label, key in (("Title", "title"), ("Site", "site"), ("Type", "type"), ("Description", "description")):
        if page[key]:
            lines.append(f"{label}: {page[key]}")
    if page["text"]:
        lines.append(f"Page text:\n{page['text']}")
    return "\n".join(lines)
