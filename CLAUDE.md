# CLAUDE.md — Project Context for Claude Code

This file provides project-specific context for Claude Code sessions. It complements (does not replace) `AGENTS.md` which contains the binding rules.

## Project Overview

This is a self-contained, portable toolkit for machine inventory, secret management, and auto-discovery. The entire project lives in this folder — nothing belongs outside except the coding agent program, `~/SECRETS`, and session history.

**Primary language:** Python 3 (stdlib only, no venv, no pip)
**Test suite:** 116 tests in `tools/tests/` (all pass, 1 skipped)

## Key Components

| Tool | Purpose | Entry Point |
|------|---------|-------------|
| `inventory.py` | Local SQLite database for machines, services, providers, models, keys, tools | `python3 tools/inventory.py` |
| `secret.py` | Secret management via OS native credential stores (WCM, Keychain, secret-tool, KWallet, TDE DCOP) | `python3 tools/secret.py` |
| `autodiscovery.py` | Auto-discovery of machine capabilities (run first on new machine) | `python3 tools/autodiscovery.py` |
| `ping_direct.py` | Direct connectivity testing | `python3 tools/ping_direct.py` |
| `gen_models_xml.py` | Generate models XML | `python3 tools/gen_models_xml.py` |
| `robota.py` | Main orchestration script | `python3 tools/robota.py` |

## Database Schema (inventory.db)

The SQLite database (`data/inventory.db`, gitignored) contains tables for:
- `machines` — discovered machines
- `services` — services running on machines
- `providers` — AI/cloud providers
- `models` — LLM models
- `keys` — API keys/credentials (references to secret store)
- `tools` — available tools on machines

Run `python3 tools/inventory.py tables` to see current schema.

## Secret Management

- **Key path scheme:** `provider/scope/kind` (e.g., `github/personal/token`, `anthropic/api/key`)
- **Primary store:** OS native credential store
- **Q4OS/TDE:** Uses `dcop kded tdewalletd` via `/opt/trinity/bin/dcop`
- **Transfer file:** `~/SECRETS` (temporary, outside project, delete after import)
- **Never commit secrets** to git or archive

## Commands Reference

### Tests
```bash
python3 -m unittest discover -s tools/tests -t . -v
```

### Inventory Database
```bash
python3 tools/inventory.py init      # Create/recreate database
python3 tools/inventory.py tables    # Show schema
python3 tools/inventory.py list machines
```

### Secret Tool
```bash
python3 tools/secret.py setup
python3 tools/secret.py probe
python3 tools/secret.py --backend file set provider/scope/kind  # Read from prompt/stdin
python3 tools/secret.py get provider/scope/kind
python3 tools/secret.py list
```
Exit codes: 0=OK, 1=not found, 2=backend error, 3=usage error

### Auto-discovery
```bash
python3 tools/autodiscovery.py
```
Exit codes: 0=OK, 1=minimum not met (git+bash missing), 2=database missing, 3=database empty

## Git Workflow

- Local commits/pushes: perform without discussion
- Remote pushes: clarify remote and branch first, then ask for explicit confirmation ("да")
- `data/inventory.db` is gitignored — never commit it

## No-Initiative Rule

**Wait for explicit order** before running commands, reading/writing files, or changing configuration. A sentence containing an action and "да" is the order and confirmation. Irreversible actions (deleting files/data, overwriting, `git push`, dropping a database) need a separate confirmation.

## Language Convention

- **User writes:** Bulgarian phonetic Latin ("pinyin BG") — do not correct or comment
- **Assistant replies:** Literary Bulgarian, Cyrillic alphabet
- **All repo files** (Markdown, Python, SQL, config, comments, commits): English

## Development Notes

- All tools use Python stdlib only — no external dependencies
- Tests are the source of truth for expected behavior
- The project is designed to be archived, moved, and unpacked — path portability matters
- On Q4OS/TDE, DCOP integration is required for wallet access