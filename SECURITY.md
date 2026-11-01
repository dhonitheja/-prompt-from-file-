# Security

## Reporting a vulnerability

Please open a private security advisory on GitHub (Security tab, "Report a vulnerability") instead of a public issue. Include steps to reproduce.

## Things to know before deploying

- The app has **no authentication**. Run it on localhost or behind an authenticating reverse proxy. Do not expose it to the internet as is. Anyone who can reach it can make your server fetch links and spend your API credits.
- **Links are fetched by your server.** To stop it being used to reach internal services, every link (and every redirect) is checked: only `http`/`https` on ports 80 and 443, and the host must resolve only to public addresses. Localhost, private networks, link-local and cloud metadata addresses are refused. Connections are pinned to the address that was checked, and downloads are limited in size and time. If you run the server inside a sensitive network, add egress firewall rules as well.
- API keys are read from environment variables only. Never commit them.
- When a cloud provider (ChatGPT or Claude) is used, what you sent goes to that service. Leave the keys unset to keep everything local. Audio is only sent to OpenAI for transcription when you choose ChatGPT or set `ALLOW_CLOUD_TRANSCRIPTION=1`.
- See `docs/threat-model.md` for the full list of risks and mitigations.
