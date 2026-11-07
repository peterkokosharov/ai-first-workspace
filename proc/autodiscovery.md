# Auto-discovery procedure

This document describes the auto-discovery workflow for the portable
workspace.  It is the expanded form of **Rule 7** in `AGENTS.md`.

## Purpose

When a new machine receives the project folder, or when a prompt needs
`tools/secret.py` or `data/inventory.db` and they are missing or unusable,
the auto-discovery script must be run before continuing.

## The script

`tools/autodiscovery.py`

Standard library only: no venv, no pip.

## What it checks

1. Operating system (name, release, version)
2. Processor architecture
3. Total RAM (MB)
4. Python version
5. Presence of `git`
6. Presence of `bash` (Git Bash on Windows)
7. Presence of `tools/secret.py`
8. Presence of `tools/inventory.py`
9. Presence of `data/inventory.db` and whether it has tables

## How to run (terminal procedure)

1. Open a terminal. On Windows, open **Git Bash**.
2. Run:

   ```bash
   python3 tools/autodiscovery.py
   ```

3. Read the output and exit code:

   | Exit code | Meaning | What to do next |
   |-----------|---------|-----------------|
   | 0 | OK, minimum met | Proceed with the task |
   | 1 | Minimum not met | Install the missing tool (git or bash) |
   | 2 | Database missing | Run `python3 tools/inventory.py init`, then repeat step 2 |
   | 3 | Database empty | Run `python3 tools/inventory.py init`, then repeat step 2 |

## Exit codes

- `0` — OK
- `1` — minimum requirement not met (missing git or bash)
- `2` — `data/inventory.db` missing
- `3` — `data/inventory.db` exists but has no tables

## Minimum requirement

- git bash + Python stdlib
- GitHub token and email are **optional** — you can work without them

## Notes printed by the script

- Secret values live in the OS native store or `--backend file` only.
- `auto` never falls back to plaintext; use `--backend file` explicitly.

## Relation to AGENTS.md

This is the concrete form of **Rule 7 — Auto-discovery procedure** in
`AGENTS.md`.  Rule 7.2 lists the exact terminal commands above.

## Related files

- `tools/autodiscovery.py` — the discovery script
- `tools/inventory.py` — creates/populates `data/inventory.db` (`init`)
- `data/schema.sql` — committed SQLite schema
- `data/seed.sql` — committed initial inventory data
- `AGENTS.md` — project rules, Rule 7
