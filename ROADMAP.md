# AI Vtuber / Agentic Assistant Platform — Roadmap

## Vision
Build a long-term, modular platform for creating **agentic AI helpers** with:
- **Consistent personality + memory** over time
- **Swappable character presentation** (puppet/avatar assets)
- **Pluggable inputs** (CLI, web, Twitch chat, games, etc.)
- **Pluggable outputs** (TTS, sprites/VTuber rigs, web UI, OBS overlays, etc.)

This repo should evolve from a single assistant into a framework for running multiple distinct assistants (“profiles”).

## Guiding Principles
- **Local-first** by default; cloud optional.
- **Composable modules**: personality, memory store, puppet assets, transports.
- **Clear interfaces** between core engine, memory, LLM, and transports.
- **Observability**: logs, prompt dumps, and auditable memory changes.

## Current Baseline (what exists today)
- Session system (STM) stored as JSON sessions
- Long-term memory (LTM) stored as `ltm.json` with confidence/strength + revision log
- Prompt construction: personality + memory block + optional OCR screen context
- LLM routing (OpenRouter) for response + reflection
- TTS (OpenAI / ElevenLabs)
- Puppet PNG viewer (Tkinter) driven by puppet directives

---

## Milestone 1 — Modular assets (Personality / Puppet / Memory) (Near-term)
**Goal:** Make editing and swapping personality, memory store, and character assets easy and modular.

Deliverables:
- Personality prompt **selectable via env var** (path or profile name)
- Puppet/character assets **selectable via env var** (e.g., puppet pack name or directory)
- Memory store file location **selectable via env var** (at least LTM; later STM too)
- Document “How to create a new character quickly”

Suggested env vars (names TBD):
- `PERSONALITY_PATH` or `PERSONALITY_NAME`
- `PUPPET_NAME` or `PUPPET_DIR`
- `LTM_PATH` (and later `SESSIONS_DIR` / `PROFILE_DIR`)

Acceptance criteria:
- Switching env vars changes personality/puppet/memory without code edits
- Defaults still work out-of-the-box

---

## Milestone 2 — Profiles (Personality + Memory + Character)
**Goal:** A “profile” bundles:
- personality prompt(s)
- memory store(s)
- puppet/character assets
- optional: voice/TTS settings, model preferences, safety settings

Deliverables:
- Profile spec (directory layout + minimal manifest)
- Profile loader + selection mechanism (env var + CLI switch)
- One or two example profiles in-repo (or documented externally)

Acceptance criteria:
- Can run two distinct assistants with isolated memory and different presentation

---

## Milestone 3 — Memory System v2 (SQLite + Embeddings + Semantic Search)
**Goal:** Improve memory quality, scalability, and retrieval.

Deliverables:
- Migrate LTM from JSON to **SQLite**
- Add embeddings table + background embedding generation
- Add retrieval:
  - semantic search (top-k)
  - recency/activation fallback (“use it or lose it”)
  - confidence-aware rendering (“MAYBE …” for medium confidence)
- Memory hygiene (deactivation/pruning) + tools to inspect/edit

Acceptance criteria:
- Memory retrieval is relevant and bounded (no runaway pileup)
- Can delete/deactivate problematic memories

---

## Milestone 4 — Platform Transports (Inputs/Outputs as plugins)
**Goal:** Treat IO as interchangeable adapters.

Deliverables:
- Transport interface(s) for inputs (CLI, web, Twitch, game events)
- Output adapters (TTS, puppet/animation, overlays)
- Event routing / message bus patterns documented

Acceptance criteria:
- Same profile can be used from CLI and a server transport with minimal change

---

## Milestone 5 — React Dashboard (Chat + Puppet + Profile Control)
**Goal:** A web dashboard for interaction and control.

Deliverables:
- React UI hosting:
  - chat
  - puppet display
  - profile selection
  - memory inspection (later)
- Server/API transport to back it

---

## Milestone 6+ — Agentic abilities & Integrations (Long-term)
Potential upgrades:
- Agentic task execution (tools, plans, retries, guardrails)
- Game API integration (context + events)
- VTube Studio integration (rig control)
- Twitch integration (chat input + output moderation)

---

## Open Questions (to resolve as we go)
- Where do profiles live (`profiles/` vs user config dir)?
- How strictly do we isolate profile state (STM/LTM/voice/model keys)?
- Which embedding provider + cost model (local vs cloud)?
- What is the stable “core” interface for transports and outputs?