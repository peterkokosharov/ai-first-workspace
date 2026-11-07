# Design Document v1 — Harness Independence and Own Runtime

Status: draft for external review
Date: 2026-11-07
Companion to: `in/design-document-v1.md`

---

## 1. Goal

The workspace must not depend on any single AI provider or any single agent harness.
If a provider changes its plan, price or terms, work continues with a different model
without rewriting prompts, tools, rules or project structure.

Target harnesses:

- Claude Code (Anthropic)
- Gemini CLI (Google)
- Codex CLI (OpenAI)
- Goose (Block)
- OpenCode
- Rex
- eventually: an own runtime

Success criterion: **switching a model is one configuration line**, and switching a
harness does not change the project.

## 2. The four layers

```
┌─────────────────────────────────────────────┐
│ 4. Project layer                            │
│    AGENTS.md, prompts, data, tools, git     │
├─────────────────────────────────────────────┤
│ 3. Harness layer                            │
│    Claude Code, Gemini CLI, Codex, Goose,   │
│    OpenCode, Rex, own runtime               │
├─────────────────────────────────────────────┤
│ 2. Gateway layer                            │
│    one endpoint, many providers             │
│    (kiko-proxy / LiteLLM / direct)          │
├─────────────────────────────────────────────┤
│ 1. Provider layer                           │
│    keys, base URLs, model IDs               │
└─────────────────────────────────────────────┘
```

The project layer is the only layer that must survive every change. If layers 1–3 are
replaced tomorrow, the folder still opens and the work continues.

## 3. Provider layer

- One key per provider, stored by key path (`provider/personal/api_key`).
- A model alias table maps human names to full model IDs (`nemotron-ultra` →
  `nvidia/nemotron-3-ultra-550b-a55b`).
- Direct access is the fallback when a gateway fails.
- Prices and context limits are recorded per model, with a date.

## 4. Gateway layer

A single local endpoint that speaks both major protocols:

- **OpenAI-compatible** `/v1/chat/completions` and `/v1/responses`;
- **Anthropic-compatible** `/v1/messages`;
- **Google-compatible** `/v1beta/models/<model>:generateContent` (for Gemini CLI).

Candidates:

| Gateway | OpenAI | Anthropic | Google | Notes |
|---|---|---|---|---|
| kiko-proxy | yes | yes | unknown | already running locally |
| LiteLLM | yes | yes | yes | heavier, mature translation |
| OpenRouter | yes | yes | partial | hosted, not local |
| Direct | yes | yes | yes | no translation, no fallback |

Rule: the gateway is **optional**. Every harness must also work directly with a
provider. The gateway is a convenience and a fallback, not a requirement.

## 5. Harness layer

### 5.1 Connection surface

| Harness | How it points elsewhere | Protocol |
|---|---|---|
| Claude Code | `ANTHROPIC_BASE_URL`, `ANTHROPIC_AUTH_TOKEN` | Anthropic Messages |
| Codex CLI | `config.toml` → `model_providers.<id>.base_url` + `env_key` | OpenAI Responses |
| Gemini CLI | `GEMINI_API_KEY`, optional base URL override | Google Generative Language |
| Goose | `config.yaml` → provider + `OPENAI_HOST` / base URL | OpenAI-compatible |
| OpenCode | `opencode.json` provider block | OpenAI-compatible |
| Rex | to be documented | to be documented |
| Own runtime | own adapter | both |

### 5.2 Instruction files

Each harness reads a different instruction file:

| Harness | File |
|---|---|
| OpenCode | `AGENTS.md` |
| Codex | `AGENTS.md` |
| Goose | `.goosehints` |
| Claude Code | `CLAUDE.md` |
| Gemini CLI | `GEMINI.md` |
| Rex | to be documented |

Single source of truth: `AGENTS.md`. The other files are **generated** from it by a
small script and carry a header "generated from AGENTS.md — do not edit". This prevents
six diverging copies of the same rules.

### 5.3 Capability differences

A model reached through a gateway is not identical to the same model inside its native
harness. Differences to expect:

- prompt caching and its pricing;
- native tool formats and parallel tool calls;
- reasoning/thinking modes;
- image and document input;
- context compaction strategy;
- safety filters and refusal behaviour.

Therefore the design does not promise "same model everywhere". It promises **same
project, comparable behaviour, measured cost**.

## 6. Project layer

The project layer is already harness-neutral:

- `AGENTS.md` — rules;
- `INVENTORY.md` — machines, services, models, keys, tools;
- `MODELS.md` — aliases and key paths;
- `in/`, `out/` — review loop;
- `tools/`, `tests/` — utilities;
- git — history.

Nothing in the project assumes a specific provider. The only provider-specific data
are model IDs and key paths, both isolated in one table.

## 7. Own runtime

### 7.1 Why

- Enforce the project rules (especially "no action without confirmation") at the
  runtime level, not by prompt discipline.
- Remove the last dependency: the harness itself.
- Own the context management and the cost accounting.

### 7.2 What a minimal runtime needs

| Component | Minimum |
|---|---|
| CLI | one command, one session |
| Provider adapter | OpenAI-compatible + Anthropic |
| Tool registry | shell, read, write, edit, grep, glob |
| Permission gate | explicit confirmation per tool class |
| Context manager | token counting, compaction |
| Session log | append-only, replayable |
| Cost ledger | tokens and USD per request |

### 7.3 What it is not

- not a product;
- not multi-user;
- not a UI;
- not a plugin ecosystem;
- not a replacement for OpenCode until it is demonstrably better for this workflow.

### 7.4 Gate

The own runtime starts only if, after phases A–D, at least one of these is true:

1. no existing harness can enforce the project rules reliably;
2. the gateway cannot provide the needed protocol coverage;
3. cost accounting cannot be obtained from existing tools.

Otherwise the runtime is a hobby, not a requirement.

## 8. Phased roadmap

| Phase | Work | Exit criterion |
|---|---|---|
| A | Gateway running with 2+ providers | one endpoint serves 2 models |
| B | Six harnesses configured | each starts a session against the gateway |
| C | Instruction-file sync | generated files match `AGENTS.md` |
| D | Switch test matrix | same task on 3 models, cost and quality recorded |
| E | Own runtime decision | gate in 7.4 evaluated |
| F | Own runtime prototype (optional) | runs one task end-to-end |

## 9. Switch test

For each candidate model:

1. run the same small task (read a file, make a change, run a test);
2. record: success/failure, wall time, input tokens, output tokens, cost, number of
   tool calls, human interventions;
3. compare against the current default.

This produces the only honest answer to "which model should I use today".

## 10. Risks

- **Terms of service.** A subscription plan and an API key are different products.
  Routing one through a third-party harness may violate the provider's terms.
- **Feature loss.** A gateway translates protocols; caching, thinking modes and native
  tools may degrade or disappear.
- **Translation bugs.** The existing kiko-proxy failure with Nemotron Ultra is an
  example: direct access works, the proxy returns HTTP 500.
- **Maintenance.** Six harnesses × N models is a matrix that grows quadratically.
  Each harness update can break its configuration.
- **Security.** One gateway is one point of compromise; one set of keys is one blast
  radius. Keys stay in the native store, never in config files.
- **Complexity without benefit.** More harnesses do not automatically mean more
  independence. The project layer is what provides independence.

## 11. Non-goals

- Supporting every harness that exists.
- Making all models behave identically.
- Building a general-purpose agent framework.
- Replacing native CLIs where they are clearly better.

## 12. Success criteria

1. Changing the model requires editing one line.
2. Changing the harness requires no change to the project.
3. The same task is reproducible on at least three models.
4. Cost per task is recorded and comparable.
5. Work continues if any single provider disappears.
6. `AGENTS.md` remains the only source of rules.
