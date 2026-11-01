# Security

## Reporting a vulnerability

Please open a private security advisory on GitHub (Security tab, "Report a vulnerability") instead of a public issue. Include steps to reproduce.

## Things to know before deploying

- **Local use is open (no login).** Keep it on localhost. To put it on a network, set `APP_PASSWORD` (HTTP Basic auth on every page and API route except `/healthz`). The Docker image runs in hosted mode and refuses to start without a password of at least 12 characters. Serve it over HTTPS, or the password travels in clear text. There is one shared password and no rate limiting, so use a long random one. Anyone with it can make your server fetch links and spend your API credits. See `docs/deploy.md`.
- **Links are fetched by your server.** To stop it being used to reach internal services, every link (and every redirect) is checked: only `http`/`https` on ports 80 and 443, and the host must resolve only to public addresses. Localhost, private networks, link-local and cloud metadata addresses are refused. Connections are pinned to the address that was checked, and downloads are limited in size and time. If you run the server inside a sensitive network, add egress firewall rules as well.
- API keys are read from environment variables only. Never commit them.
- When a cloud provider (ChatGPT or Claude) is used, what you sent goes to that service. Leave the keys unset to keep everything local. Audio is only sent to OpenAI for transcription when you choose ChatGPT or set `ALLOW_CLOUD_TRANSCRIPTION=1`.
- See `docs/threat-model.md` for the full list of risks and mitigations.
