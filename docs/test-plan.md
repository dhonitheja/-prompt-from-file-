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
| Page served | `test_index_served` |

## Checked by hand during development (one-off, not automated)
- **Video (US-2):** a real 3-second MP4 produced 6 frames and a prompt; a corrupt file returned a clear 400.
- **Pinned-address TLS (ADR-8):** against a local HTTPS server with a self-signed certificate, a request pinned to the checked IP succeeded when the certificate matched the name and failed when it did not.

## Not yet verified (manual before release)
- Real model quality with Ollama, ChatGPT and Claude: confirm each returns the Prompt / Negative prompt / Key details format.
- Real speech transcription with `faster-whisper` and with OpenAI.
- Real websites, app store pages, game pages and a YouTube link: confirm what is and isn't read, and that the notes are accurate.
- Browser check: previews for image/video/audio, link box, provider dropdown, notes, copy button.

## Exit criteria
All automated tests pass, lint is clean, no vulnerable dependencies, no open Critical or High findings, manual checks above done once per release.
