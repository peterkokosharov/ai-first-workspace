# Project Rules

This folder is self-contained and portable: archive it, move it, unpack it, work continues.
Nothing belongs outside except the coding agent program, `~/SECRETS`, and session history.

## Language

- User writes in Bulgarian phonetic Latin ("pinyin BG") — do not correct or comment.
- Assistant replies in literary Bulgarian, Cyrillic alphabet.
- All repo files (Markdown, Python, SQL, config, comments, commits) are in English.

## No initiative

Wait for an explicit order before running commands, reading/writing files, or changing
configuration. A sentence containing an action and "да" is the order and confirmation.
Irreversible actions (deleting files/data, overwriting, `git push`, dropping a database)
need a separate confirmation.

## First commands on a new machine

```bash
python3 tools/autodiscovery.py
python3 tools/inventory.py init
python3 -m unittest discover -s tools/tests -t . -v
```

- `autodiscovery.py` exit codes: 0 OK, 1 minimum not met (git + bash missing),
  2 database missing, 3 database empty.
- Tests: 116 total. On Windows several fail because optional tools are absent
  (docker, node, npm, opencode, native secret stores) — that is expected, not a bug.
  One test is skipped unless `SECRET_LIVE_TESTS=1` (live DCOP write/read/delete on Q4OS).

## Inventory database (local, gitignored — recreate if missing)

```bash
python3 tools/inventory.py init
python3 tools/inventory.py tables
python3 tools/inventory.py list machines
```

`data/inventory.db` is never committed. Rebuild from `data/schema.sql` + `data/seed.sql`.

## Secrets

Secret values never enter git or the archive. Primary store is the OS native credential
store (WCM, Keychain, secret-tool, KWallet, TDE DCOP). Key path scheme:
`provider/scope/kind` (e.g. `github/personal/token`).

```bash
python3 tools/secret.py setup
python3 tools/secret.py probe
python3 tools/secret.py --backend auto set provider/scope/kind   # read value from prompt/stdin
python3 tools/secret.py get provider/scope/kind
python3 tools/secret.py list
```

Exit codes: 0 OK, 1 not found, 2 backend error, 3 usage error. `auto` never falls back
to plaintext — use `--backend file` explicitly. `~/SECRETS` is a temporary export file
outside the project — delete after import.

## Inventory first

Before asking about machines, services, providers, models, keys or tools, check
`data/inventory.db` with `python3 tools/inventory.py`.

## Git

- `git commit` / `git push` locally: perform without discussion.
- `git push remote`: clarify remote and branch first, then ask for explicit confirmation ("да").
- `data/inventory.db` is gitignored — never commit it.

## Available tools

- `tools/secret.py` — secret tool over native credential stores.
- `tools/inventory.py` — SQLite inventory manager (init, tables, list, show, search, sql read-only, setting).
- `tools/autodiscovery.py` — machine discovery (OS, RAM, CPU, Python, git, bash, inventory db).
- `tools/ping.py` — ping a model via OpenCode and verify against inventory.
- `tools/ping_direct.py` — direct HTTP ping to providers (gemini, nvidia, deepseek, mistral).
- `tools/setup_providers.py` — configure OpenCode providers from KWallet keys.
- `tools/robota.py` — scrape build.nvidia.com/models into `kb/md/` and `kb/html/`.
- `tools/gen_models_xml.py` — generate `kb/models.xml` from the scraped index.

## Requirements

- Python 3.x (stdlib only; no venv, no pip)
- git
- node.js + npm — only for `mermaid-cli` diagrams (`npx -y @mermaid-js/mermaid-cli`)
- One supported agent harness (OpenCode primary; Claude Code, Codex CLI, Gemini CLI, Rex secondary)

## Output

Write audit reports and test artifacts to `out/` (gitignored, not committed).
