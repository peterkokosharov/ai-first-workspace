# Project Rules

Self-contained, portable folder: archive it, move it, unpack it, work continues.
Nothing belongs outside except the coding agent program, `~/SECRETS`, and session history.

## Language

- User writes in Bulgarian phonetic Latin ("pinyin BG") — do not correct or comment.
- Assistant replies in literary Bulgarian, Cyrillic alphabet.
- All repo files (Markdown, Python, SQL, config, comments, commits) are in English.

## Commands (exact)

Tests:
```
python3 -m unittest discover -s tools/tests -t . -v
```
57 tests pass. One skipped unless `SECRET_LIVE_TESTS=1` (live DCOP on Q4OS).

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
python3 tools/secret.py --backend file set provider/scope/kind
python3 tools/secret.py get provider/scope/kind
python3 tools/secret.py list
```
Exit codes: 0 OK, 1 not found, 2 backend error, 3 usage error. `auto` never falls back to plaintext — use `--backend file` explicitly.

Auto-discovery (run first on a new machine):
```
python3 tools/autodiscovery.py
```
Exit codes: 0 OK, 1 minimum not met, 2 database missing, 3 database empty.

Diagrams (Mermaid → SVG):
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

Before asking about machines, services, providers, models, keys or tools, check
`data/inventory.db` with `python3 tools/inventory.py`.

## No initiative

Wait for an explicit order before running commands, reading/writing files, or changing
configuration. A sentence containing an action and "да" is the order and confirmation.
Irreversible actions (deleting files/data, overwriting, `git push`, dropping a database)
need a separate confirmation.

## Requirements

- Python 3.x (stdlib only; no venv, no pip)
- git
- node.js + npm — for `mermaid-cli` diagrams
- One supported agent harness (OpenCode primary)

## License

`LICENSE` — MIT License, copyright 2026 Peter Kokosharov.
