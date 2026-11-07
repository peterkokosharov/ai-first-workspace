# Portable Development Workspace

A self-contained, portable folder for AI-assisted software development. The folder
itself is the product: rules, inventory, tooling, notes and configuration live here.
It can be archived, moved to another machine, unpacked and continued without missing
pieces.

Status: **v1 draft / pre-project**. Some components described below are planned and
not yet implemented; they are marked as such.

## Goals

The workspace answers three questions at any time:

1. **What do we have?** — machines, services, model providers, models, keys, tools.
2. **How do we use it safely?** — where secrets live, what may read them, what is
   forbidden.
3. **How do we continue on another machine?** — what travels in the archive, what is
   recreated, what is verified afterwards.

A second goal is **independence**: switching a model or a provider must not require
rewriting prompts, tools, rules or the project structure.

Success criterion: archive the folder → move it to another machine → unpack it → open
it with a coding agent → work continues, with no file left behind on the old machine.

## Repository layout

```text
./
├── AGENTS.md              # the six project rules (Bulgarian)
├── README.md              # this file
├── KEYS                   # secret names and model table (no values)
├── MODELS.md              # models, providers and key names (no values)
├── PLAN-secret.md         # plan for the secret tool (Bulgarian)
├── in/                    # review inputs: design documents and task briefs
├── out/                   # review outputs: one critique per model
├── tools/                 # planned: secret.py, inventory.py, autodiscovery.py
├── tests/                 # planned: unit tests
├── schema.sql             # planned: SQLite schema
├── seed.sql               # planned: initial inventory data
├── inventory.db           # local only, never committed
├── assets/fonts/          # planned: bundled Cyrillic fonts
└── .tmp/                  # temporary files, not versioned
```

## Current components

- `AGENTS.md` — the only source of project rules. Six rules: language, records,
  self-containment, technical requirements, working habits, and no action without
  explicit confirmation.
- `KEYS` — the names of the secrets and of the models. Contains no values.
- `MODELS.md` — model aliases, full model IDs, providers, and the key each model uses.
- `PLAN-secret.md` — the plan for the secret tool, including key paths, backends,
  migration, and the temporary export file.
- `in/` — design documents and the review brief.
- `out/` — independent critiques produced by different models.

## Planned components

These are described in the design documents and are not implemented yet:

- `secret.py` — one interface over native credential stores. Intended commands:
  `get`, `set`, `del`, `list`, `export`, `import`, `setup`, `probe`. Agents should use
  a `run`/`exec` mode that injects a value into a child process instead of printing it.
- `inventory.py` — manages the local SQLite inventory (`inventory.db`): machines,
  services, model providers, models, keys, tools, and the active model choice.
- `autodiscovery.py` — on a new machine, detects the OS, Python, installed agent
  harnesses and available credential store; creates `inventory.db` from `schema.sql`
  and seed data; guides the user through populating the native store and the inventory.
- `schema.sql` and `seed.sql` — database structure and initial data, committed to git
  so a new machine can rebuild the database.
- `tests/` — unit tests for the three scripts.
- `assets/fonts/` — bundled fonts with full Cyrillic support.

## Secrets

- Secret values never enter git, the archive, or any project file.
- The primary store is the operating system's native credential store: Windows
  Credential Manager, macOS Keychain, GNOME Keyring, or KWallet.
- `~/SECRETS` is a temporary export/transfer file outside the project. It is created
  only for transfer, backup, or a machine without a working store, and is deleted
  after a successful import.
- Inside the repository only names and paths are recorded: `KEYS` and `MODELS.md`.
- `inventory.db` is local and is never committed.

## Harness independence

The same project must work with different agent harnesses. Fallback order:

1. Claude Code
2. Codex CLI
3. Gemini CLI
4. OpenCode
5. Rex

If none is available, install OpenCode. If that is not possible, install Rex. Work
continues either way.

No local LLM is used: on the available hardware it is too slow to be practical.

## How to continue on another machine

Intended flow, once the planned scripts exist:

1. Clone the repository.
2. Make sure Python 3 and git are available.
3. Run `python3 autodiscovery.py`.
4. Populate the native credential store with the keys listed in `KEYS`.
5. Let `autodiscovery.py` create and populate `inventory.db`.
6. Choose a model from `MODELS.md`.
7. Start a session with any available harness.

## Design documents and review loop

- `in/design-document-v1.md` — whole-project design (English).
- `in/design-runtime-v1.md` — harness independence and a possible own runtime
  (English). Not part of the current review round.
- `in/task.md` — the review brief given to external models.
- `out/` — one critique per model, in English.

The review loop is simple: a design document and a task brief go into `in/`, several
models critique them, and the critiques land in `out/`. Nothing in `in/` or `out/` is
authoritative; the authoritative records are `AGENTS.md`, `MODELS.md` and, later,
`INVENTORY.md`.

## Language

Project records are written in Bulgarian, as required by `AGENTS.md`. This README is
in English by explicit request. The external review artifacts in `in/` and `out/` are
also in English so that external models can review them.

## Requirements

- Python 3.x (with the standard `sqlite3` module)
- git
- One supported agent harness, or the ability to install one
- A native credential store, or the temporary export file as a fallback
