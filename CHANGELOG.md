# Changelog

## Unreleased

### Added
- Upload an image, video, PDF or text file and get a reverse-engineered prompt.
- Providers: local Ollama (default), ChatGPT and Claude, with an Auto mode that falls back in that order.
- Provider selector on the upload page and a `provider` API field.
- Tests, CI (lint, tests, dependency scan), and project docs.

### Fixed
- Uploads are read up to the size limit only, instead of buffering the whole body first.
- Video processing has timeouts and checks for both `ffmpeg` and `ffprobe`.
- A malformed reply from a model now returns a clean 502 instead of a 500.
