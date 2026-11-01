# Threat Model

Assets: the user's files and links, API keys, the host machine and the networks it can reach.
Trust boundaries: browser/API client to server; server to model providers; **server to any URL a client supplies**.

| # | Threat | Impact | Mitigation | Status |
|---|---|---|---|---|
| T1 | Huge upload or linked file exhausts memory | Server crash | Read at most `MAX_UPLOAD_MB`+1 bytes; stream link downloads with a cap; 413 | Done |
| T2 | Crafted video hangs or abuses ffmpeg | CPU exhaustion | Timeouts on ffprobe and ffmpeg; fixed argument list, no shell; private temp dir | Done |
| T3 | Command injection through the filename | Code execution | Filename is never passed to a command; only its extension names a temp file | Done |
| T4 | Prompt injection inside a file, image, transcript or web page | Model output manipulated | Output is shown as text only and never executed or used to take actions | Accepted, low impact |
| T5 | Data unexpectedly sent to a cloud provider | Privacy loss | Cloud used only when a key is set or explicitly chosen; page shows which model answered; audio needs an explicit opt-in | Done |
| T6 | API key leakage | Account abuse | Keys only from environment; `.gitignore` excludes `.env`; keys are not logged or returned | Done |
| T7 | Unauthenticated access if exposed to a network | Anyone can use your model, credits and server | Shared password (HTTP Basic, constant-time compare) on every page and API route except `/healthz`; hosted mode (`HOSTED=1`, set in the Docker image) refuses to start without a password of 12+ characters | Done for hosting; local mode stays open by design |
| T8 | Vulnerable dependencies | Various | `pip-audit` in CI | Done |
| T9 | Cross-site scripting in the page | Script injection | Model output, notes and errors are inserted with `textContent`, never as HTML | Done |
| T10 | Malformed PDF crashes the parser | 500 error for that request | No shared state between requests | Accepted |
| T11 | **SSRF:** a link to `localhost`, a private network or a cloud metadata address makes the server call internal services | Internal data exposure, credential theft | Scheme and port allow-list; every resolved address must be public; connection pinned to the checked IP; redirects re-validated; no credentials in URLs are forwarded | Done |
| T12 | DNS rebinding (name resolves to a public IP at check time, a private one at connect time) | Bypasses T11 | Connect to the already-checked IP, with `Host`/SNI set to the real name | Done |
| T13 | Redirect to an internal address | Bypasses T11 | Redirects are not auto-followed; each `Location` goes through all checks; max 5 | Done |
| T14 | Slow or endless response from a linked site | Worker held open | 10 s socket timeouts and a 20 s overall deadline; byte cap | Done |
| T15 | A linked site fingerprints or tracks the server | Minor | Fixed generic User-Agent, no cookies, no stored state | Accepted |
| T16 | Server used as an open proxy to hit third-party sites | Abuse of your IP | Public-only, GET-only, size and time limits; behind the T7 password | Mitigated by the password |
| T18 | Password guessing (no rate limit, one shared password) | Attacker uses your credits | 12-character minimum, generated random value on Render, HTTPS from the platform, constant-time comparison; use provider spending caps | **Open, Medium** for hosting: add rate limiting if it will be shared widely |
| T19 | Password sent over plain HTTP | Password theft | Docs require HTTPS; hosting platforms terminate TLS | Done (documented) |
| T20 | A logged-in user runs up API costs | Unexpected bill | Size limit; one shared trust circle; spending caps at the provider | Accepted |
| T21 | Clickjacking or script injection via the page | Session abuse | `X-Frame-Options: DENY`, `frame-ancestors 'none'`, a Content-Security-Policy, `nosniff`, no HTML built from model output | Done |
| T17 | A linked page tricks the model into describing something false | Misleading prompt | `notes` states results come from page metadata; user reviews the prompt | Accepted |

No Critical or High risk is open for local use or for hosting behind HTTPS with a strong password. T18 (password guessing) is the main open item for hosting; it becomes High if the password is short or the URL is widely shared.
