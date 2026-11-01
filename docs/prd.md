# Product Requirements: Prompt from File

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

## Scope
In: single-file upload, web page, JSON API, three model backends.

## Non-goals
- Audio files (planned, not in this version).
- Accounts, history, or storing uploads.
- Recovering the real original prompt or hidden metadata. Output is a reconstruction.
- Multi-user hosting. There is no authentication (see `SECURITY.md`).

## Top risks
1. Local vision models can give weak prompts. Mitigation: configurable model, cloud fallback.
2. Files sent to cloud models leave the machine. Mitigation: local default, explicit keys, documented.
3. Large or hostile uploads exhaust memory or CPU. Mitigation: size cap, timeouts (see threat model).
