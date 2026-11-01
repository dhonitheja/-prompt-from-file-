# Contributing

1. Install dev tools: `pip install -r requirements-dev.txt`
2. Make your change in a small branch and open a pull request.
3. Before pushing, run `ruff check .` and `pytest -q`. CI runs both plus a dependency scan.
4. Add or update a test for any behavior change. Model backends are mocked in `tests/`, so no API keys or Ollama are needed.
5. Record notable decisions in `docs/architecture.md` (Decisions section) and user-visible changes in `CHANGELOG.md`.

Definition of done: tests pass, lint is clean, README and docs match the behavior, no secrets in the diff.
