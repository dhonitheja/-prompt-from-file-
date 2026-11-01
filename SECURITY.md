# Security

## Reporting a vulnerability

Please open a private security advisory on GitHub (Security tab, "Report a vulnerability") instead of a public issue. Include steps to reproduce.

## Things to know before deploying

- The app has **no authentication**. Run it on localhost or behind an authenticating reverse proxy. Do not expose it to the internet as is.
- API keys are read from environment variables only. Never commit them.
- When a cloud provider (ChatGPT or Claude) is used, the uploaded file is sent to that service. Leave the keys unset to keep everything local.
- See `docs/threat-model.md` for the full list of risks and mitigations.
