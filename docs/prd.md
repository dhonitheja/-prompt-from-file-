# Product Requirements: Prompt from File

**Status:** Approved by the owner on 2026-10-31, including the non-goals below.

## Problem
People who see an image or video they like want to recreate or vary it with an AI generation tool, but writing a good prompt from scratch is slow. People with a document or code file sometimes want the instruction that would regenerate it.

## Users
- **Creator:** wants a paste-ready prompt for an image or video tool from a reference file.
- **Privacy-conscious user:** wants this to work without uploading files to a third party.

## User stories and acceptance criteria

| ID | Story | Acceptance criteria |
|---|---|---|
| US-1 | As a creator, I upload an image and get a prompt that recreates it. | Returns Prompt, Negative prompt and Key details. Supports JPEG, PNG, GIF, WebP. |
| US-2 | I upload a video and get one prompt covering the whole clip. | Frames are sampled and sent together; the prompt covers motion and camera work. |
| US-3 | I upload a PDF or text/code file and get the instruction that would generate it. | PDF text is extracted; text files up to 100,000 characters are used. |
| US-4 | I keep my files on my machine. | The default mode uses only a local model. No file leaves the machine unless a cloud key is set and a cloud model is used. |
| US-5 | I choose which model answers, or let it fall back. | Page and API accept Auto, Local, ChatGPT, Claude. Auto tries local, then ChatGPT, then Claude, skipping any without a key. The answering model is shown. |
| US-6 | I add context such as "for Midjourney". | The optional note is passed to the model. |
| US-7 | I get clear errors. | Unsupported type, empty file, oversized file, unreachable or misbehaving model each return a specific message, never a crash. |
| US-8 | I paste a link to a website, app or game and get a prompt to recreate it. | The page's title, description, text and preview image are read. The response says that videos, apps and games are not opened or played. Pages with no readable content return a clear message. |
| US-9 | I paste a direct link to an image, video, audio, PDF or text file. | It is downloaded (within the size limit) and handled like an upload. |
| US-10 | I upload audio and get a prompt from what is said. | Speech is transcribed locally when possible. Audio is only sent to a cloud service when I choose ChatGPT or opt in. A file with no speech returns a clear message. |
| US-11 | Pasting a link cannot be used to reach my private network. | Localhost, private, link-local and metadata addresses are refused, including via redirects. |
| US-12 | I can host it online and only I (and people I give the password to) can use it. | A Docker image runs on a standard host; every page and API route requires a shared password; the hosted image won't start without a strong one. Added 2026-10-31 at the owner's request. |

## Scope
In: single-file upload or single link, web page, JSON API, three model backends, speech transcription.

## Non-goals
- Analyzing music, tone of voice or sound effects (speech only), and the audio track of videos.
- Playing videos, running apps or games, logging in to sites, or reading pages that need JavaScript to show anything.
- Game and app binaries (executables, ROMs, installers). Use screenshots, gameplay video or the store link.
- Accounts, history, or storing uploads.
- Recovering the real original prompt or hidden metadata. Output is a reconstruction.
- Multi-user accounts, per-user limits or billing. Hosting uses one shared password (see `docs/deploy.md`).

## Top risks
1. Local vision models can give weak prompts. Mitigation: configurable model, cloud fallback.
2. Files sent to cloud models leave the machine. Mitigation: local default, explicit keys, documented.
3. Large or hostile uploads exhaust memory or CPU. Mitigation: size cap, timeouts (see threat model).
4. Link fetching lets someone make the server call internal services (SSRF). Mitigation: address checks on every hop, pinned connection, port and scheme limits.
5. Link results look authoritative but are based only on page metadata. Mitigation: a `notes` field states exactly what was and was not analyzed.
