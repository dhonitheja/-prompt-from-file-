# Test Plan

## Approach
Automated tests in `tests/test_app.py` run the API with all model backends mocked, so they need no Ollama and no API keys. CI runs lint, tests and a dependency scan on every push and pull request.

## Requirement traceability

| Requirement | Test |
|---|---|
| US-1 image prompt | `test_image_is_sent_to_vision_model` |
| US-3 PDF and text | `test_pdf_text_extracted`, `test_local_default` |
| US-4 local by default | `test_local_default` |
| US-5 provider choice and fallback | `test_auto_falls_back_to_chatgpt`, `test_auto_falls_back_to_claude_when_only_claude_key`, `test_explicit_claude_sends_key_header`, `test_explicit_ollama_does_not_fall_back` |
| US-6 note | `test_note_is_forwarded` |
| US-7 errors | `test_unsupported_type_415`, `test_empty_file_400`, `test_too_large_413`, `test_bad_provider_400`, `test_ollama_down_no_keys_returns_502`, `test_explicit_cloud_without_key_502`, `test_malformed_model_response_is_502_not_500` |
| Page served | `test_index_served` |

## Not covered by automated tests (manual before release)
- US-2 video: needs `ffmpeg` and a real clip. Check a short MP4 returns a prompt and a corrupt file returns a clear error.
- Real model quality with Ollama, ChatGPT and Claude: confirm each returns the Prompt / Negative prompt / Key details format.
- Browser check: upload preview, provider dropdown, copy button.

## Exit criteria
All automated tests pass, lint is clean, no vulnerable dependencies, no open Critical or High findings, manual checks above done once per release.
