# Threat Model

Assets: the user's uploaded files, API keys, the host machine.
Trust boundary: the browser/API client to the server; the server to model providers.

| # | Threat | Impact | Mitigation | Status |
|---|---|---|---|---|
| T1 | Huge upload exhausts memory | Server crash | Read at most `MAX_UPLOAD_MB`+1 bytes, reject with 413 | Done |
| T2 | Crafted video hangs or abuses ffmpeg | CPU exhaustion | Timeouts on ffprobe and ffmpeg; fixed argument list, no shell; input written to a private temp dir | Done |
| T3 | Command injection through the filename | Code execution | Filename is never passed to a command; only its extension is used to name a temp file | Done |
| T4 | Prompt injection inside an uploaded file or image | Model output manipulated | Output is shown as text only and never executed or used to take actions | Accepted, low impact |
| T5 | Files unexpectedly sent to a cloud provider | Privacy loss | Cloud used only when a key is set or explicitly chosen; page shows which model answered; documented | Done |
| T6 | API key leakage | Account abuse | Keys only from environment; `.gitignore` excludes `.env`; keys are not logged or returned | Done |
| T7 | Unauthenticated access if exposed to a network | Anyone can use your model and cloud credits | Documented as local-only; run behind an authenticating proxy | Open, documented in `SECURITY.md` |
| T8 | Vulnerable dependencies | Various | `pip-audit` in CI | Done |
| T9 | Stored XSS in the page | Script injection | Model output is inserted with `textContent`, not HTML | Done |
| T10 | Malformed PDF crashes the parser | 500 error | pypdf errors surface as a server error for that request only; no state is shared | Accepted |

No Critical or High risk is open for the intended local use. T7 becomes High if the app is deployed on a public network.
