# Audit task for project folder

You are asked to perform a read-only audit of this project folder
(`/home/petark/Documents/Default Project`).

## What to check

1. `AGENTS.md` — does it define the project rules clearly?
   - Language rule (English records, Bulgarian chat)
   - Records rule (Markdown format)
   - Self-containment rule (everything stays in this folder)
   - Technical requirements (UTF-8, fonts, stdlib only)
   - Working habits (read before change, no initiative without permission)
   - No action without explicit permission
   - Git operation rules (Rule 6.7)

2. `README.md` — does it describe what the project is and how to continue working?
   - Goals, repository layout, current components
   - Secrets handling, KWallet/TDE DCOP notes
   - How to continue on another machine
   - Requirements

3. Python scripts — do they exist and work?
   - `tools/secret.py` — portable secret tool over native stores
   - `tools/inventory.py` — SQLite inventory manager
   - `tools/autodiscovery.py` — machine discovery script
   - `tools/ping.py` — model ping via OpenCode
   - `tools/ping_direct.py` — direct HTTP ping to providers
   - `tools/setup_providers.py` — configure OpenCode providers from KWallet

4. Tests — are they functional (not assertEquals(1,1))?
   - `tools/tests/` with `secret.py`, `inventory.py`, `autodiscovery.py`
   - Run: `python3 -m unittest discover -s tools/tests -t . -v`
   - All tests pass? Any skipped?

5. Data files — are they committed correctly?
   - `data/schema.sql`
   - `data/seed.sql`
   - `data/inventory.db` (local only, gitignored)

6. Vendored library
   - `lib/kikolib` — copied from `~/kiko/packages/kikolib/kikolib`
   - `lib/README.md` — provenance and license

7. `.gitignore` — does it exclude `data/inventory.db`, `__pycache__`, `.tmp/`?

8. `proc/autodiscovery.md` — auto-discovery procedure (Rule 7 detail)

9. `in/task.md` — this audit task file itself

10. What is missing? What would you add or change?

## Output format

- You may ONLY read files. Do not write, edit, delete, or run any commands
  that modify the project folder.
- Write your findings to a new file in `out/` (for example `out/audit-<model>.md`).
- Use Markdown. Write in English.
- Do not print secret values. Do not print the contents of `~/SECRETS` or any
  KWallet entries.

## Expected outcome

A concise audit report covering: what is good, what is missing, what is broken,
and recommendations for next steps.
