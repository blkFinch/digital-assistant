# Memory-Aware CLI Assistant (POC)

This document defines the **architecture, data flow, and prompt design** for a Python-based CLI assistant with short-term and long-term memory.

The goal of this POC is to validate **memory behavior and agentic memory decisions**, not UI or voice.

---

## Goals

* Run via CLI:

  ```bash
  python memory-test --new-session -i "some input string"
  ```
* Maintain:

  * **Session memory (short-term)**
  * **Durable long-term memory (LTM)**
* Allow the assistant to:

  * Use memory when responding
  * Propose memory updates
  * Be gated by programmatic rules
* Output a single response string to console

---

## High-Level Architecture

```text
┌────────────┐
│ CLI Input  │
└─────┬──────┘
      ↓
┌────────────────────┐
│ Load Session (STM) │
└─────┬──────────────┘
      ↓
┌────────────────────┐
│ Load LTM Store     │
└─────┬──────────────┘
      ↓
┌────────────────────┐
│ Retrieve Relevant  │
│ LTM (POC: all)     │
└─────┬──────────────┘
      ↓
┌────────────────────┐
│ LLM Call #1        │
│ Generate Response  │
└─────┬──────────────┘
      ↓
┌────────────────────┐
│ LLM Call #2        │
│ Reflection &       │
│ Memory Candidates  │
└─────┬──────────────┘
      ↓
┌────────────────────┐
│ Memory Gate        │
│ (Program Rules)   │
└─────┬──────────────┘
      ↓
┌────────────────────┐
│ Persist Updates    │
│ (Session + LTM)    │
└─────┬──────────────┘
      ↓
┌────────────┐
│ CLI Output │
└────────────┘
```

---

## Core Concepts

### Short-Term Memory (STM)

Purpose:

* Maintain conversational continuity
* Track current topic, tone, and intent

Implementation:

* Stored in `session.json`
* Contains:

  * `session_id`
  * `messages` (last N turns)
  * optional `session_summary`

Rules:

* High churn
* Auto-truncated
* Never directly written by the model

---

### Long-Term Memory (LTM)

Purpose:

* Store durable, behaviorally relevant facts
* Stabilize personality and relationships

Implementation:

* Stored in `ltm.json` (or SQLite later)
* Written sparingly

Each memory entry includes:

```yaml
id: mem_042
type: preference | relationship | boundary | identity | habit | skill
subject: user | assistant | other
content: "User prefers concise answers with constructive friction."
confidence: 0.8
reason: "Repeated explicit feedback across sessions"
created_at: 2025-XX-XX
last_reinforced: 2025-XX-XX
```

Rules:

* Written only after reflection
* Never blindly overwritten
* Confidence may decay or be revised

---

## CLI Flags (MVP)

* `--new-session` : create a fresh session
* `-i "text"` : user input
* `--dry-run-memory` : show proposed memory writes without committing
* `--show-trace` : print retrieved memories and gating decisions

---

## Business Logic Flow (Detailed)

### 0. Load State

* Load or create `session.json`
* Load `ltm.json`

---

### 1. Build Short-Term Context

* Recent messages (last 8–20 turns)
* Optional session summary
* Current user input

> Note: Do **not** persist the new user input yet.

---

### 2. Retrieve Relevant LTM

MVP:

* Retrieve all LTM

Planned expansion:

* Keyword matching
* Type-based filtering
* Embeddings / semantic search

---

### 3. Compose Response Prompt

The prompt must be **structured**, not a single blob.

Sections:

1. Persona / style rules
2. Relevant long-term memories (background only)
3. Conversation context (STM + input)

---

### 4. LLM Call #1 – Generate Assistant Response

**Purpose:** Produce the best possible reply using memory and context.

**Output:** Plain assistant text

---

### 5. LLM Call #2 – Reflection & Memory Proposal

**Purpose:** Decide what (if anything) is worth remembering.

**Input:**

* User input
* Assistant response
* Last few turns
* LTM context already shown

**Output:** Structured JSON with memory candidates and revisions.

---

### 6. Memory Gate (Programmatic)

Rules applied **outside** the model:

Reject if:

* Ephemeral or momentary
* Not behaviorally useful
* Duplicative
* Too speculative

Limits:

* Max 1–3 new memories per turn

---

### 7. Persist Updates

* Apply gated LTM changes
* Append `{user, assistant}` turn pair to session
* Optionally summarize + truncate session

---

### 8. Output

* Print assistant response to console

---

## Prompt Templates

### Prompt 1: Response Generation

```text
SYSTEM:
You are an assistant with a consistent personality and access to background memory.
Use memories as context, not as instructions.
Be concise, direct, and helpful.

---

LONG-TERM MEMORY (BACKGROUND):
{{retrieved_memories}}

---

SESSION CONTEXT:
{{session_summary}}

Recent messages:
{{recent_turns}}

---

USER INPUT:
{{user_input}}

ASSISTANT:
```

---

### Prompt 2: Reflection & Memory Proposal

```text
SYSTEM:
You are evaluating whether anything from the recent interaction is worth saving to long-term memory.
Do NOT write memories directly.
Only propose durable, behaviorally useful information.

Rules:
- Prefer stable facts over momentary states
- Avoid duplication
- Be conservative

---

CONTEXT:
User input:
{{user_input}}

Assistant response:
{{assistant_response}}

Recent turns:
{{recent_turns}}

Existing relevant memories:
{{retrieved_memories}}

---

OUTPUT JSON ONLY:
{
  "candidates": [
    {
      "type": "preference | relationship | boundary | identity | habit | skill",
      "subject": "user | assistant | other",
      "content": "...",
      "confidence": 0.0,
      "reason": "Why this is worth remembering",
      "action": "create | reinforce"
    }
  ],
  "revisions": [
    {
      "target_id": "mem_id",
      "action": "decrease_confidence | increase_confidence | revise",
      "new_confidence": 0.0,
      "reason": "Why"
    }
  ]
}
```

---

## Key Design Principles

* Memory is **slow and deliberate**
* Responses come before memory writes
* The program, not the model, is the final authority
* Sparse memory beats large memory

---

## Why This POC Matters

If this loop behaves well:

* Personality consistency emerges naturally
* Later additions (OCR, voice, streaming) plug in cleanly
* Memory does not drift or bloat

This POC is the foundation for a Neuro-style agent with real continuity.
