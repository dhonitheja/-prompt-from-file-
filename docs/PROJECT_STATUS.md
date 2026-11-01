# Project Status

**Current phase:** 6 Release, prepared. Waiting on the first CI run of the Docker job and the owner's deploy.
**Updated:** 2026-10-31

## Gate checklist

| Phase | Gate | State |
|---|---|---|
| 1 Discover | PRD signed off, top risks listed | Done: `docs/prd.md` (12 user stories; scope signed off by the owner on 2026-10-31; US-12 hosting added at the owner's request) |
| 2 Design | Reviewed design, measurable NFRs, threat model with mitigations | Done: `docs/architecture.md` (9 ADRs, 10 NFRs), `docs/threat-model.md` (21 threats) |
| 3 Plan | First slice small and shippable | Done: slices for files, links and audio, and hosting are built |
| 4 Build | DoD met: tests with code, CI config | Done: 69 tests, ruff clean, CI with lint, tests, dependency scan and a Docker job |
| 5 Verify | No open Critical/High; QA exit criteria met | Partly: automated checks pass, `pip-audit` clean, video, pinned-TLS and the hosted app in a real browser checked by hand. Real models, real sites, real transcription and the Docker image are not yet verified (see `docs/test-plan.md`) |
| 6 Release | Staging, deploy pipeline, rollback, runbooks, monitoring | Partly: Dockerfile, health check, `render.yaml`, deploy guide and a post-deploy checklist are written. Not deployed. Rollback is redeploying a previous commit. No monitoring beyond the platform's health check and logs |
| 7 Operate and learn | SLOs, incidents, feedback loop | Not started |

## Open risks
- **T18 (Medium, hosting):** one shared password and no rate limiting. Use a long random password and set spending caps at OpenAI/Anthropic.
- The Docker image has never been built (no Docker daemon where it was written); CI will be the first build.
- Link results depend on what a page exposes in its HTML. JavaScript-only pages return little (the response says so).
- Audio: speech only. Hosted audio needs cloud transcription (opt-in).
- Real-world quality of models, transcription and live sites is untested.

## Decisions needed from the owner
1. Which host? The docs cover Render (config included) and any Docker host.
2. Which cloud key(s) will it use (ChatGPT, Claude, or both), and a monthly spending cap.

## Next 3 actions
1. Check that the CI run on GitHub is green, especially the new `docker` job.
2. Deploy using `docs/deploy.md`, then run its post-deploy checklist.
3. Rename the GitHub repo to remove the stray dashes (`-prompt-from-file-`); update the clone URL in the README afterward.
