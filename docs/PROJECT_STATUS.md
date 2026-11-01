# Project Status

**Current phase:** 5 Verify (automated part done), manual verification pending.
**Updated:** 2026-10-31

## Gate checklist

| Phase | Gate | State |
|---|---|---|
| 1 Discover | PRD signed off, top risks listed | Done: `docs/prd.md` (awaiting owner sign-off) |
| 2 Design | Reviewed design, measurable NFRs, threat model with mitigations | Done: `docs/architecture.md`, `docs/threat-model.md` |
| 3 Plan | First slice small and shippable | Done: the app is a single slice and already built |
| 4 Build | DoD met: tests with code, CI config | Done: 16 tests, ruff clean, CI workflow added |
| 5 Verify | No open Critical/High; QA exit criteria met | Partly: automated checks pass, `pip-audit` clean; real-model and video checks are manual (see `docs/test-plan.md`) |
| 6 Release | Staging, deploy pipeline, rollback, runbooks, monitoring | Not applicable yet: local tool, no hosted deployment |
| 7 Operate and learn | SLOs, incidents, feedback loop | Not started |

## Open risks
- T7: no authentication. Fine for local use, High if exposed publicly.
- Video and real-model output quality are untested on real inputs.
- Local vision models vary widely in quality.

## Decisions needed from the owner
1. Sign off the PRD scope, including the audio non-goal.
2. Is hosted deployment wanted? If yes, authentication and a deploy pipeline come first.

## Next 3 actions
1. Run the manual checks in `docs/test-plan.md` with a real Ollama model and a short video.
2. Rename the GitHub repo to remove the stray dashes (`-prompt-from-file-`).
3. Decide on audio support (transcribe, then prompt) for the next slice.
