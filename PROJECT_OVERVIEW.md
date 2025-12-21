# OCR Screen Assistant – Build Plan (v1.1)

## Goal

Build a local-first assistant that:

* Reads **text from the desktop screen using OCR**
* Answers **typed questions** about what’s visible
* Uses a **hybrid LLM setup** (Ollama by default, OpenRouter when needed)
* Responds via **text + TTS** (voice input added later)

This is a Neuro-style foundation focused on *screen understanding*, not vision.

---

## Core Behavior (v1)

1. User presses a hotkey
2. App captures a screenshot (full screen or region)
3. OCR extracts visible text
4. User types a question about the screen
5. LLM answers using OCR text as context
6. TTS reads the answer aloud

Limitations (intentional):

* OCR-only → understands **text**, not icons or images
* Best for errors, logs, docs, menus, chat, UI labels

---

## Architecture Overview

**Single local orchestrator (Python)**

Inputs:

* Screenshot text (OCR)
* Typed question
* Optional: active window title / app name

Persistent State:

* **Memory of past events** (screen events, questions, answers, notable moments)
* Short-term context (last interactions)
* Long-term summaries ("what keeps happening")

Processing:

* OCR preprocessing + cleanup
* Memory retrieval (relevant past events)
* Prompt construction (current screen + memory + question)
* LLM routing (local vs cloud)

Outputs:

* Text response
* Spoken response (TTS)

---

## Tool Stack

### Screen Capture

* `mss` (cross-platform, fast)
* Optional (Windows): `dxcam`

### OCR

* `easyocr`
* `opencv-python` (grayscale, resize, thresholding)

### LLMs

* **Ollama** (default, private)
* **OpenRouter** (fallback for complex queries)

### TTS

Choose one:

* ElevenLabs (best quality)
* Piper (local, fast)
* Coqui TTS (local, heavier)

### UI / Control

* Hotkeys: `keyboard` (Win) or `pynput`
* Simple UI: terminal first, optional `tkinter` later

---

## Build Phases

> **Important:** Memory is a first-class feature. Even in text-only mode, the assistant should record and recall past events so personality and continuity emerge early.

### Phase 1 – Text-Only Screen Assistant

**Goal:** typed question → OCR → memory-aware LLM → text answer

Steps:

1. Capture screenshot (full screen initially)
2. Preprocess image (OpenCV)
3. Run OCR (EasyOCR)
4. Clean OCR text (remove junk lines, normalize whitespace)
5. **Store event in memory**:

   * timestamp
   * active app/window
   * OCR text hash or summary
   * user question
6. Retrieve **relevant past events** (recent + similar)
7. Build structured prompt:

   * App/window info
   * OCR text (current)
   * Retrieved memory snippets
   * User question
8. Query Ollama

Checkpoint:

* Can ask: "What does this error mean?" and get a useful answer that can reference earlier screens or questions

---

### Phase 2 – Add TTS

**Goal:** spoken answers

Steps:

* Feed final response to TTS
* Enforce short responses (2–6 sentences)
* Optionally summarize before speaking

Checkpoint:

* Typed question → spoken response

---

### Phase 3 – Hybrid LLM Routing

**Goal:** local-first, cloud when needed

Routing rules (initial):

* Use OpenRouter if:

  * OCR text > ~6–10k chars
  * User explicitly asks
  * Local model fails repeatedly

Optional compression:

1. Local model summarizes OCR text
2. Summary + question sent to OpenRouter

---

## Memory Design (Added Early)

Memory should exist **before speech**, so continuity is baked in.

### What to Store

* Screen events (OCR summaries, not raw images)
* User questions
* Assistant answers
* Explicit notes ("this keeps failing", "remember this")

### How to Store

* Simple local store first:

  * JSONL or SQLite
* Each entry:

  * timestamp
  * app/window
  * short text summary
  * tags (error, doc, config, etc.)

### Retrieval Strategy (v1)

* Always include:

  * last N interactions (short-term memory)
* Optionally include:

  * keyword matches
  * same app/window matches

Later upgrades:

* Embeddings
* Event summarization / consolidation

---

## Key Design Rules

### Region Capture Matters

* Full-screen OCR is noisy
* Add later:

  * Active window only
  * Region select
  * Reuse last region

### OCR Accuracy

* Preprocessing is mandatory
* Prefer fewer, cleaner lines over raw dumps

### Prompt Discipline

* Always separate:

  * OCR facts
  * User question
* Keep responses actionable

### Voice Constraints

* Short
* No rambling
* Max one clarifying question

---

## Safety / Privacy Notes

* Cloud calls may expose sensitive screen text
* Before OpenRouter:

  * Redact tokens, keys, emails (regex-based is fine)
  * Optionally require user confirmation

---

## Future Extensions

* Voice input (Whisper)
* OCR region memory
* On-screen captions via OBS
* Persona / character layer
* CV-based vision (optional, later)

---

## Status

This document defines **v1.1 scope** and acts as the reference plan for future iterations.
