# Design Document v1 — Portable Development Workspace

Status: draft for external review
Date: 2026-11-07
Author: project maintainer with AI assistance
Language note: this document is in English by request, so that external models can
review it. All other project records stay in Bulgarian, as required by the project
rules.

---

## 1. Purpose

This project is a **self-contained, portable workspace** for AI-assisted software
development. It is not an application. It is the folder in which work happens:
rules, inventory, tooling, notes and configuration all live here, and the folder can
be archived, moved to another machine, unpacked and continued without missing pieces.

The workspace must answer three questions at any time:

1. **What do we have?** — machines, services, model providers, models, keys, tools.
2. **How do we use it safely?** — where secrets live, who may read them, what is
   forbidden.
3. **How do we continue on another machine?** — what travels in the archive, what is
   recreated, what is verified afterwards.

Success criterion: archive → move → unpack → open with the coding agent → work
continues, with no file left behind on the old machine.

## 2. Core principles

The project is governed by six rules (full text in `AGENTS.md`):

1. **Language.** The user writes in phonetic Latin; the assistant replies in literary
   Bulgarian, Cyrillic. Records are in Bulgarian.
2. **Records.** All notes and documentation are Markdown (`.md`), in Bulgarian.
3. **Self-containment.** Everything project-related stays inside the folder. Paths are
   relative. Configuration is local. Fonts and resources are bundled. Dependencies are
   local or restorable from a lockfile. Temporary files go to `.tmp/`. The root
   `README.md` is the entry point. Secrets never enter the archive or git; values live
   outside the project.
4. **Technical requirements.** UTF-8 everywhere. Only fonts with Cyrillic support,
   shipped with the project.
5. **Working habits.** Read before changing. Follow surrounding style. Explain what
   changed and where. Never delete or overwrite someone else's work without consent.
6. **No initiative.** The agent performs no action — no shell command, no file read or
   write, no configuration change, no test — without an explicit order and a
   confirmation. A question gets an answer only. Ambiguity is treated as a question.

Rule 6 is the most important behavioural constraint: the assistant is an executor,
not a driver. It may propose, but it does not act unasked.

## 3. Repository layout

```
./
├── AGENTS.md                 # the six rules (Bulgarian)
├── README.md                 # entry point (planned)
├── INVENTORY.md              # the map of everything (planned)
├── MODELS.md                 # models and key names (no values)
├── PLAN-secret.md            # plan for the secret tool (Bulgarian)
├── KEYS                      # legacy; to be replaced by INVENTORY.md
├── .gitignore                # excludes .tmp/
├── in/                       # review inputs (design documents, task briefs)
├── out/                      # review outputs (critiques)
├── tools/                    # small utilities (planned: secret.py)
├── tests/                    # unit tests (planned)
└── .tmp/                     # temporary files (not versioned)
```

Notes:

- `in/` and `out/` are used for the model-review loop: a design document and a task
  brief are placed in `in/`, several models critique them, critiques land in `out/`.
- Nothing in `in/` or `out/` is authoritative. The authoritative records are
  `AGENTS.md`, `INVENTORY.md` and `MODELS.md`.

## 4. Inventory model

The inventory is the heart of the workspace. It is a set of small tables, each with an
explicit purpose. Every row has a **status** (`active`, `planned`, `broken`, `retired`).

### 4.1 Machines

| Name | OS | Arch | Python | User | Role |
|---|---|---|---|---|---|
| `q4os` | Q4OS Linux (TDE) | x86_64 | 3.x (to verify) | `petark` (sudo via root) | primary |
| `win10` | Windows 10 | x86_64 | 3.13 | `Dani` | secondary |

### 4.2 Services (not models)

Services are external systems used for work, regardless of whether they expose an API.

| Service | Kind | Account | Key | Status |
|---|---|---|---|---|
| GitHub | code hosting | personal | `github/personal/token` | active |
| Gmail | mail | personal | — | active |
| Facebook | social | — | — | to clarify |
| Jira | issue tracking | — | — | planned |
| Confluence | documentation | — | — | planned |

A service may have **zero, one or many** credentials. Multiple credentials are
distinguished by scope in the key path, not by ad-hoc names.

### 4.3 Model providers and models

| Model alias | Full model | Provider | Key |
|---|---|---|---|
| `gemini-flash-lite` | `gemini/gemini-3.5-flash-lite` | gemini | `gemini/personal/api_key` |
| `gemini-flash` | `gemini/gemini-3.8-flash` | gemini | `gemini/personal/api_key` |
| `nemotron-ultra` | `nvidia/nemotron-3-ultra-550b-a55b` | nvidia | `nvidia/personal/api_key` |
| `nemotron-super-vl` | `nemotron-3.5-super-vl-free` | opencode | — (free) |
| `llama` | `groq/llama-3.3-70b-versatile` | groq | `groq/personal/api_key` |
| `qwen-coder` | `openrouter/qwen/qwen3.8-27b:free` | openrouter | `openrouter/personal/api_key` |
| `deepseek-chat` | `deepseek-chat` | deepseek | `deepseek/personal/api_key` |
| `mistral-small` | `mistral/mistral-small-latest` | mistral | `mistral/personal/api_key` |

The alias is what humans say ("use Nemotron Ultra"); the full model is what the API
expects; the provider groups models; the key path says which credential pays for it.

### 4.4 Tools and environments

| Tool | Machine | Status |
|---|---|---|
| Python | q4os, win10 | active |
| Git | q4os | active |
| Docker | — | planned |
| Windows 10 SDK | win10 | planned |
| MSVC + linker | win10 | planned |

Tools that require installation are recorded as `planned` and installed separately.
The inventory records the decision, not the installation itself.

## 5. Secret management

### 5.1 Key path scheme

Secrets are identified by a path, not by a flat name:

```
provider / scope / kind
```

Examples:

```
github/personal/token
github/work/prj1/token
github/work/prj2/token
nvidia/personal/api_key
gemini/personal/api_key
```

- first segment: provider (the issuer);
- last segment: kind (`token`, `api_key`, `password`, `secret`);
- middle: scope, with as many levels as needed (`personal`, `work/prj1`).

Why paths:

- no collisions between personal and project credentials;
- the same string can be used as the target name in Windows Credential Manager;
- adding a project does not change the schema.

### 5.2 Backends

The tool has one interface and several backends:

| Platform | Native store | Fallback |
|---|---|---|
| Windows 10 | Credential Manager (`cmdkey`) | export file |
| macOS | Keychain (`security`) | export file |
| Mint / GNOME | GNOME Keyring (`secret-tool`) | export file |
| Q4OS / KDE / TDE | KWallet (DCOP) | export file |
| Headless / unknown | — | export file |

**Native store is primary.** The export file is temporary: it exists only for
transfer, backup, or a machine without a working store, and is deleted after import.

### 5.3 Export file format

`~/SECRETS` (outside the project, mode `600`), two columns:

```
# KEY_PATH | value
github/personal/token | ghp_...
nvidia/personal/api_key | nvapi-...
```

- split on the **first** `|` only;
- `#` comments and blank lines ignored;
- duplicate paths are an error;
- written atomically (temp file, `chmod 600`, `os.replace`).

This is the only file that ever contains values. It is never inside the project,
never in git, never in the archive.

### 5.4 CLI

```
secret.py get  <path>                 # prints only the value
secret.py set  <path> [--stdin]       # value from stdin or prompt
secret.py del  <path>
secret.py list [--json]               # names only, never values
secret.py export --out -              # to stdout
secret.py import --in -               # from stdin
secret.py setup                       # detect OS store, offer to create/import
secret.py probe                       # test a store without real secrets
```

- `--backend {auto,file,kwallet,keyring,wcm,keychain}`;
- default is `auto`: native store if available and unlocked, otherwise file;
- `set` reads from stdin, not argv, to keep values out of shell history and `ps`;
- exit codes: `0` ok, `1` not found, `2` backend error, `3` usage error.

### 5.5 First run on a new machine

1. Unpack the archive.
2. Run `secret.py setup`.
3. The tool detects the OS and the available store; if none exists it asks
   "no credential store found — create one?".
4. Values come from a separately transferred export file or are entered manually.
5. If no store can be used, the tool writes `secrets-import.txt` with
   `KEY_PATH = value` lines for manual import.
6. The export is deleted after a successful import.

The archive itself never carries values, so the tool must say this explicitly rather
than fail silently.

### 5.6 Security properties

- Values never appear in `list`, `probe` or logs.
- File mode is always `600` after any write.
- Atomic writes; no partial files.
- No network access from the tool.
- The tool does not decide policy: it only reads and writes.

## 6. Portability and recovery

The portability test is part of the design, not an afterthought:

1. archive the folder;
2. move to another machine;
3. unpack;
4. open with the coding agent;
5. run `secret.py setup`;
6. verify: `secret.py list` shows the expected paths, `get` returns values, tests pass.

What is **not** in the archive: program installation (OpenCode), the secrets file,
session history, system packages. These are recreated or configured once per machine.

Recovery: the export file is the backup of last resort. If a native store is lost, the
values can be re-imported from a recent export. Therefore exports must be taken
periodically, but they are not kept in the project folder.

## 7. Governance and workflow

- **Rule 6:** no action without an explicit order and a confirmation.
- **Decision log:** design decisions are recorded in Markdown, with date and reason.
- **Versioning:** git commits mark milestones (`v1 - initial release`,
  `v2 - inventory`, ...). The repository is local; a remote is optional.
- **Review loop:** design documents go to `in/`, several models critique them into
  `out/`, the maintainer reads the critiques and decides what changes.
- **Language:** English is allowed for external review artifacts; everything else is
  Bulgarian.

## 8. Current state (2026-11-07)

- Project rules: 6 rules, 27 clauses.
- Git: local repository, branch `main`, commit `v1 - initial release`.
- Secrets: 7 keys (6 real API keys + 1 GitHub token). One key
  (`deepseek/personal/api_key`) currently holds a placeholder, not a real key.
- Models: 8 entries (2 Gemini, 1 NVIDIA, 1 free OpenCode, 1 Groq, 1 OpenRouter,
  1 DeepSeek, 1 Mistral).
- Machines: 2.
- Known issues:
  - `kiko-proxy` returns HTTP 500 for Nemotron Ultra, while direct NVIDIA access works;
  - `~/github_token` has mode `664` (readable by other users);
  - no `README.md` yet;
  - `KEYS` and `MODELS.md` duplicate content (to be merged into `INVENTORY.md`);
  - `~/SECRETS` currently mixes values and a model table (to be cleaned).

## 9. Roadmap

| Phase | Work | Result |
|---|---|---|
| 0 | Probe KWallet (DCOP, wallet name, unlock behaviour) | decision on primary backend |
| 0.5 | Collect every secret on the machine into one list | complete source inventory |
| 1 | Key paths + file backend + CLI + tests | working tool without KWallet |
| 2 | KWallet backend + mocked tests | second backend if phase 0 succeeds |
| 3 | Migration + `INVENTORY.md` | new inventory replaces `KEYS` |
| 4 | Documentation + commit | milestone `v2` |

Phase 1 does not depend on phase 0 and can start immediately.

## 10. Risks

- **Locked KWallet.** DCOP calls may block or require a GUI. The probe uses a
  3-second timeout and falls back to the file backend.
- **Undocumented DCOP interface.** Method names are discovered at runtime; hence the
  probe is a separate step.
- **Values containing `|`.** Mitigated by splitting on the first separator only, with
  an explicit test.
- **Two sources of truth.** The native store is primary; the file is an export. The
  tool must never treat both as writable at the same time.
- **Free models change.** `big-pickle` and other free models are time-limited; the
  design must not depend on any single model.
- **Over-engineering.** The workspace is intentionally small. Features are added only
  when a real need appears.

## 11. Non-goals

- No server, database or sync service.
- No GUI.
- No secret values in git, the archive, or any project file.
- No full rework of LiteLLM or kiko-proxy.
- No automatic installation of SDKs or toolchains.
- No model evaluation harness beyond the simple review loop.

## 12. Open questions

1. What is the KWallet wallet name, and does it unlock automatically at login?
2. Should `set` ask for confirmation before overwriting an existing path?
3. Do work credentials (`github/work/prj1`, `prj2`) get values on this machine, or
   are they only described in the inventory?
4. Exact Python version on `q4os`.
5. Are SSH and GPG keys in scope, or explicitly out of scope?
6. How often is an export taken for backup?

## 13. Glossary

- **Native store** — the OS-provided credential manager (WCM, Keychain, Keyring,
  KWallet).
- **Export** — the temporary `~/SECRETS` file with values, used for transfer/backup.
- **Key path** — `provider/scope/kind`, the stable name of a secret.
- **Alias** — the short human name of a model.
- **Stealth model** — an unreleased model hosted under a codename for testing.
