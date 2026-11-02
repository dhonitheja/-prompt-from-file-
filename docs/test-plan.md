# Test Plan

## Approach
Automated tests in `tests/` run the API with every model backend and all network access mocked, so they need no Ollama, no API keys and no internet. CI runs lint, tests and a dependency scan on every push and pull request.

## Requirement traceability

| Requirement | Test |
|---|---|
| US-1 image prompt | `test_image_is_sent_to_vision_model` |
| US-3 PDF and text | `test_pdf_text_extracted`, `test_local_default` |
| US-4 local by default | `test_local_default`, `test_audio_not_sent_to_cloud_unless_chatgpt_chosen` |
| US-5 provider choice and fallback | `test_auto_falls_back_to_chatgpt`, `test_auto_falls_back_to_claude_when_only_claude_key`, `test_explicit_claude_sends_key_header`, `test_explicit_ollama_does_not_fall_back`, `test_link_with_provider_choice` |
| US-6 note | `test_note_is_forwarded` |
| US-7 errors | `test_unsupported_type_415`, `test_empty_file_400`, `test_too_large_413`, `test_bad_provider_400`, `test_neither_file_nor_link_400`, `test_both_file_and_link_400`, `test_ollama_down_no_keys_returns_502`, `test_explicit_cloud_without_key_502`, `test_malformed_model_response_is_502_not_500` |
| US-8 web page link | `test_web_page_link`, `test_missing_preview_image_is_a_note_not_an_error`, `test_page_with_no_content_422` |
| US-9 direct file link | `test_direct_image_link`, `test_audio_link`, `test_link_too_large_413` |
| US-10 audio | `test_audio_transcribed_locally`, `test_audio_without_speech_422`, `test_audio_without_backend_501`, `test_audio_cloud_transcription_when_chatgpt_chosen` |
| US-11 / NFR-7 no private-network access | `test_unsafe_links_rejected` (14 cases), `test_hostname_resolving_to_private_address_rejected`, `test_host_with_one_private_address_rejected`, `test_redirect_to_private_address_rejected`, `test_redirect_is_followed`, `test_redirect_loop_rejected`, `test_http_error_status_400` |
| US-12 / NFR-9 / NFR-10 hosting login and headers | `test_pages_require_password` (4 routes), `test_api_requires_password`, `test_correct_password_any_username`, `test_wrong_credentials_rejected` (8 cases), `test_healthz_is_open`, `test_hosted_mode_requires_strong_password`, `test_local_mode_needs_no_password`, `test_security_headers_always_present` |
| US-13 target tool | `tests/test_targets.py`: default, all 7 targets, case and spacing, unknown target rejected before any model call, target with a note, every target offered on the page |
| US-2 video (needs ffmpeg; skipped if absent) | `tests/test_video.py`: sent as one image, the sheet is a real wide JPEG with the expected frame count, the instruction says it is one video in time order, video defaults to a video-style prompt, an explicit target overrides it, images are unaffected, notes explain the sheet |
| Page served | `test_index_served` |

## Checked by hand during development (one-off, not automated)
- **Video (US-2):** a real 3-second MP4 produced 6 frames and a prompt; a corrupt file returned a clear 400.
- **Pinned-address TLS (ADR-8):** against a local HTTPS server with a self-signed certificate, a request pinned to the checked IP succeeded when the certificate matched the name and failed when it did not.

- **Hosted mode in a real browser (Chromium via Playwright):** the app started the way the container starts it. No credentials and a wrong password gave 401; `/healthz` was open; after logging in, an image upload showed a preview and returned a result; a private-address link showed the refusal message; no Content-Security-Policy violations. Starting with `HOSTED=1` and no password exited with an error.

- **Target dropdown in a real browser:** choosing Midjourney and then Voiceover sent the matching instruction to the model each time.

## Not yet verified (manual before release)
- **Does each target really produce a better prompt?** The tests prove the instruction is sent, not that the model follows it well. Judge a few real outputs per target, especially with small local models.
- **The Docker image itself:** the Docker daemon was unavailable where this was built, so the image was never built or run here. The CI `docker` job builds it, checks it refuses to start without a password, and smoke-tests login and ffmpeg. The first green CI run is the proof.
- **An actual deployment** (Render or other): not done from here; use the checklist in `docs/deploy.md`.
- Real model quality with Ollama, ChatGPT and Claude: confirm each returns the Prompt / Negative prompt / Key details format.
- Real speech transcription with `faster-whisper` and with OpenAI.
- Real websites, app store pages, game pages and a YouTube link: confirm what is and isn't read, and that the notes are accurate.
- Browser check: previews for image/video/audio, link box, provider dropdown, notes, copy button.

## Exit criteria
All automated tests pass, lint is clean, no vulnerable dependencies, no open Critical or High findings, manual checks above done once per release.
