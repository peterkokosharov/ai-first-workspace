# Portable Development Workspace

A self-contained, portable folder for AI-assisted software development. The folder
itself is the product: rules, inventory, tooling and configuration live here.
It can be archived, moved to another machine, unpacked and continued without missing
pieces.

Status: **v5 — tooling implemented and tested; auto-discovery added**.

## Goals

The workspace answers three questions at any time:

1. **What do we have?** — machines, services, model providers, models, keys, tools.
2. **How do we use it safely?** — where secrets live, what may read them, what is
   forbidden.
3. **How do we continue on another machine?** — what travels in the archive, what is
   recreated, what is verified afterwards.

Success criterion: archive the folder → move it to another machine → unpack it → open
it with a coding agent → work continues, with no file left behind on the old machine.

## Repository layout

```text
./
├── AGENTS.md              # the project rules (English)
├── README.md              # this file
├── lib/                   # vendored libraries (kikolib from upstream)
│   └── kikolib/           # standard-library keystore and factory
├── data/
│   ├── schema.sql         # committed SQLite schema
│   ├── seed.sql           # committed initial inventory data
│   └── inventory.db       # local only, never committed (gitignored)
├── proc/
│   └── autodiscovery.md   # auto-discovery procedure (Rule 7 detail)
├── tools/
│   ├── __init__.py
│   ├── secret.py          # portable secret tool over native stores
│   ├── inventory.py       # SQLite inventory manager
│   ├── autodiscovery.py   # machine discovery: OS, RAM, Python, git, bash, db
│   └── tests/             # functional tests
│       ├── __init__.py
│       ├── secret.py      # tests for tools/secret.py
│       ├── inventory.py   # tests for tools/inventory.py
│       ├── autodiscovery.py # tests for tools/autodiscovery.py
│       ├── test_secret.py # unittest shim for discover
│       ├── test_inventory.py # unittest shim for discover
│       └── test_autodiscovery.py # unittest shim for discover
├── .gitignore
└── .tmp/                  # temporary files, not versioned
```

## Current components

- `AGENTS.md` — the single source of project rules: language, records,
  self-containment, technical requirements, working habits, no action without
  explicit confirmation, and git operation rules. Project records are in English;
  chat with the assistant is in Bulgarian Cyrillic.
- `lib/kikolib` — vendored copy of `~/kiko/packages/kikolib/kikolib` (MIT), providing
  `kikolib.factory` (backend registry/selection) and `kikolib.keystore` (native
  credential-store calls: WCM, Keychain, `secret-tool`, KWallet, TDE DCOP).
- `tools/secret.py` — portable secret tool over native credential stores. Backends:
  `memory`, `file`, `wcm`, `keychain`, `secret-tool`, `kwallet`, `dcop`. Commands:
  `get`, `set`, `del`, `list`, `export`, `import`, `probe`, `setup`, `run`, `exec`.
  Default key path scheme: `provider/scope/kind` (e.g. `github/personal/token`).
  `auto` never falls back to plaintext; use `--backend file` explicitly.
- `tools/inventory.py` — manages the local SQLite inventory (`data/inventory.db`):
  `init`, `tables`, `list`, `show`, `search`, `sql` (read-only), `setting`.
- `tools/autodiscovery.py` — discovers the local environment before running:
  OS, processor, RAM, Python version, git, bash (Git Bash on Windows), presence of
  `tools/secret.py` and `tools/inventory.py`, and whether `data/inventory.db`
  exists and has tables. Exit codes: 0 OK, 1 minimum not met, 2 database missing,
  3 database empty.
- `tools/tests/` — functional tests (not `assertEquals(1,1)`). Run:
  `python3 -m unittest discover -s tools/tests -t . -v`.
  Live DCOP write/read/delete runs only with `SECRET_LIVE_TESTS=1`.
- `proc/autodiscovery.md` — expanded form of Rule 7 in `AGENTS.md`; describes the
  terminal procedure when `secret.py` or `inventory.db` are missing or unusable.

## Secrets

- Secret values never enter git, the archive, or any project file.
- The primary store is the operating system's native credential store: Windows
  Credential Manager, macOS Keychain, GNOME Keyring/`secret-tool`, KWallet, or TDE
  DCOP on Q4OS.
- `~/SECRETS` is a temporary export/transfer file outside the project. It is created
  only for transfer, backup, or a machine without a working store, and is deleted
  after a successful import.
- `data/inventory.db` is local and is never committed. It is rebuilt from
  `data/schema.sql` and `data/seed.sql` with `python3 tools/inventory.py init`.

## KWallet / TDE DCOP (Q4OS)

On Q4OS/TDE the wallet daemon lives inside `kded`, so it is reached with
`dcop kded tdewalletd`. The `dcop` binary is at `/opt/trinity/bin` and may not be on
`PATH`; `secret.py` prepends it automatically. The wallet must be enabled
(`Enabled=true` in `~/.trinity/share/config/tdewalletrc`) and opened once
manually (`isOpen kdewallet` must return `true`). Live DCOP tests are skipped unless
`SECRET_LIVE_TESTS=1`.

## Developed and tested on OpenCode

This project is developed and tested on **OpenCode**. All commands, tests, and
workflows in this README are verified on OpenCode first:

- `python3 -m unittest discover -s tools/tests -t . -v` — all 57 tests pass
- `python3 tools/secret.py` — secret tool over native stores
- `python3 tools/inventory.py` — SQLite inventory manager
- `python3 tools/autodiscovery.py` — machine discovery

OpenCode is the primary harness for this project. Other harnesses (Claude Code,
Codex CLI, Gemini CLI, Rex) are supported but secondary.

## Harness independence

The same project must work with different agent harnesses. Fallback order:

1. OpenCode
2. Claude Code
3. Codex CLI
4. Gemini CLI
5. Rex

If none is available, install OpenCode. If that is not possible, install Rex. Work
continues either way.

No local LLM is used: on the available hardware it is too slow to be practical.

## How to continue on another machine

1. Clone the repository.
2. Make sure Python 3 and git are available.
3. Run `python3 tools/autodiscovery.py` to verify the environment.
4. Run `python3 tools/inventory.py init` to create `data/inventory.db`
   (from `data/schema.sql` + `data/seed.sql`).
5. Populate the native credential store with the key paths from the inventory
   (`provider/scope/kind`).
6. Verify: `python3 tools/secret.py setup` and `python3 tools/secret.py probe`.
7. Run tests: `python3 -m unittest discover -s tools/tests -t . -v`.
8. Start a session with any available harness.

## Language

Project records are written in English, as required by `AGENTS.md`. This README is in
English. Communication with the assistant is in Bulgarian Cyrillic (chat language).

## Requirements

- Python 3.x (stdlib only; no venv, no pip)
- git
- One supported agent harness, or the ability to install one
- A native credential store, or the temporary export file as a fallback
