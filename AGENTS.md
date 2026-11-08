# Project Rules

This folder is self-contained and portable: archive it, move it, unpack it, work continues. Nothing belongs outside except the coding agent program, `~/SECRETS`, and session history.

## Language

- User writes in Bulgarian phonetic Latin ("pinyin BG") — do not correct or comment.
- Assistant replies in literary Bulgarian, Cyrillic alphabet.
- All repo files (Markdown, Python, SQL, config, comments, commits) are in English.

## Commands (exact)

Tests:
```
python3 -m unittest discover -s tools/tests -t . -v
```
116 tests pass. One test skipped unless `SECRET_LIVE_TESTS=1` (live DCOP write/read/delete on Q4OS).

Inventory database (local, gitignored — recreate if missing):
```
python3 tools/inventory.py init
python3 tools/inventory.py tables
python3 tools/inventory.py list machines
```

Secret tool (stdlib only, no venv, no pip):
```
python3 tools/secret.py setup
python3 tools/secret.py probe
python3 tools/secret.py --backend auto set provider/scope/kind   # read value from prompt/stdin
python3 tools/secret.py get provider/scope/kind
python3 tools/secret.py list
```
Exit codes: 0 OK, 1 not found, 2 backend error, 3 usage error. `auto` never falls back to plaintext — use `--backend file` explicitly.

Auto-discovery (run first on a new machine):
```
python3 tools/autodiscovery.py
```
Exit codes: 0 OK, 1 minimum not met (git + bash missing), 2 database missing, 3 database empty.

Mermaid diagrams (optional):
```
npx -y @mermaid-js/mermaid-cli -i doc/diagrams/<name>.mmd -o doc/diagrams/<name>.svg -t default -b white
```
Requires `node.js` + `npm`.

## Git

- `git commit` / `git push` locally: perform without discussion.
- `git push remote`: clarify remote and branch first, then ask for explicit confirmation ("да").
- `data/inventory.db` is gitignored — never commit it.

## Secrets

- Secret values never enter git or the archive.
- Primary store is the OS native credential store (WCM, Keychain, secret-tool, KWallet, TDE DCOP).
- `~/SECRETS` is a temporary export/transfer file outside the project — delete after import.
- On Q4OS/TDE the wallet is reached via `dcop kded tdewalletd` (`/opt/trinity/bin/dcop`).
- Key path scheme: `provider/scope/kind` (e.g. `github/personal/token`).

## Inventory first

Before asking about machines, services, providers, models, keys or tools, check `data/inventory.db` with `python3 tools/inventory.py`.

## No initiative

Wait for an explicit order before running commands, reading/writing files, or changing configuration. A sentence containing an action and "да" is the order and confirmation. Irreversible actions (deleting files/data, overwriting, `git push`, dropping a database) need a separate confirmation.

## Requirements

- Python 3.x (stdlib only; no venv, no pip)
- git
- node.js + npm — for `mermaid-cli` diagrams
- One supported agent harness (OpenCode primary; Claude Code, Codex CLI, Gemini CLI, Rex supported but secondary)

## Available tools

- `tools/secret.py` — secret tool over native credential stores (`get`, `set`, `del`, `list`, `export`, `import`, `probe`, `setup`, `run`, `exec`).
- `tools/inventory.py` — SQLite inventory manager (`init`, `tables`, `list`, `show`, `search`, `sql` read-only, `setting`).
- `tools/autodiscovery.py` — machine discovery (OS, RAM, CPU, Python, git, bash, python, node, docker, npm, docker-compose, opencode, merman, presence of tools, inventory db). Reads runtime paths from `settings.json`.
- `tools/ping.py` — ping a model via OpenCode and verify against inventory database.
- `tools/ping_direct.py` — ping LLM providers directly via HTTP (gemini, nvidia, deepseek, mistral) using keys from inventory database.
- `tools/setup_providers.py` — configure OpenCode providers from keys in inventory.
- `tools/robota.py` — scrape `build.nvidia.com/models` for free-endpoint models into `kb/md/` and `kb/html/`.
- `tools/gen_models_xml.py` — generate `kb/models.xml` from the scraped index.
- `tools/bootstrap.sh` — one-command init: `init` → `autodiscovery.py` → reminders → tests.

## Output

Write audit reports and test artifacts to `out/` (gitignored, not committed).

## Data

`data/schema.sql` and `data/seed.sql` are committed. `data/inventory.db` is local and gitignored — recreate with `python3 tools/inventory.py init`.

## License

`LICENSE` — MIT License, copyright 2026 Peter Kokosharov.