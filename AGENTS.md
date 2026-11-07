# Project Rules

This file is the single source of rules for the project. The whole project — code,
records, configuration, fonts and resources — lives in this folder.

## Rule 1 — Language

1.1. The user writes in "pinyin BG" (phonetic Bulgarian written with Latin letters),
for example `zdr. haide da suzdadem agents.md`. This is normal: do not correct it and
do not comment on it.

1.2. The assistant replies in literary Bulgarian, written in Cyrillic.
- Always use the Cyrillic alphabet in replies (not Latin transliteration).
- Use correct grammar, punctuation and capitalisation.
- Keep terms, file names, commands and code in their original form (Latin) when
  precision requires it.

1.3. All files in the repository are written in English: Markdown, Python, SQL,
configuration, comments and commit messages. Communication with other agents is also
in English.

## Rule 2 — Records

2.1. Records — notes, documentation, plans, logs, task lists and explanations — are
written in English and in Markdown (`.md`).

2.2. Code and data keep their natural format: `.py`, `.java`, `.cpp`, `.ts`, `.js`,
`.html`, `.svg`, `.json`, `.db`, `.ttf`, and so on. The `.md` rule applies to records,
not to code or data.

2.3. The working and communication format of the project is Markdown. `AGENTS.md`,
the documents in `in/`, the reviews in `out/` and the design documents are `.md`.

2.4. Unless another format is explicitly required, records are made in `.md`.

## Rule 3 — Everything stays in this folder (self-containment and portability)

The folder is self-contained and portable: it is archived, moved to another machine,
unpacked and opened with a coding agent — and work continues without missing parts.

3.1. Nothing that belongs to the project is scattered outside the folder on disk. No
files in the home directory, no global configuration, no changes in system
directories. The only declared exceptions are `~/SECRETS` (temporary export) and the
native credential store (WCM, Keychain, GNOME Keyring, KWallet), which are external by
design.

3.2. The ban in 3.1 applies to disk files, not to the network. Uploading data to the
internet is allowed when the task requires it, except for secrets (see 3.9).

3.3. All paths are relative to the root of the folder. No absolute or
machine-dependent paths. The exceptions are `~/SECRETS` and native-store paths, which
are external by design.

3.4. The OpenCode configuration for the project is local — in `opencode.json(c)` or
`.opencode/` (agents, commands, skills, permissions, plugins). The project does not
rely on global configuration.

3.5. Fonts and resources are in the folder (for example `assets/fonts/`). Do not rely
on system fonts.

3.6. Dependencies are local or restorable from a lockfile. No global installations and
no changes to the system.

3.7. Temporary files go in `.tmp/` in the folder and are not required to continue the
work.

3.8. Entry point: `README.md` in the root briefly describes what the project is and how
to continue working on it.

3.9. Secrets never enter the archive or git. Values live in the operating system's
native credential store: Windows Credential Manager, macOS Keychain, GNOME Keyring or
KWallet. `~/SECRETS` is a temporary export/transfer file outside the project; it is
deleted after a successful import. The folder contains only `KEYS` — the names of the
secrets and the path to the store, without values. On another machine, `~/SECRETS` is
recreated.

3.10. Portability test: archive the folder → transfer it to another machine → unpack it
→ open it with a coding agent → work continues. Run this test when moving to another
machine or after a major change, not after every edit.

3.11. Only these remain outside the folder: the coding agent program, `~/SECRETS`,
session history and system packages. They are set up once on a new machine and are not
part of the project. "Work continues" means the project work, not the chat history.

## Rule 4 — Technical requirements

4.1. Encoding: all files are written in UTF-8.

4.2. Fonts: use only fonts with full Cyrillic support, shipped with the project (see
3.5).
- Preferred: `DejaVu Sans`, `Noto Sans`, `Liberation Sans`, `Fira Sans`, `Roboto`,
  `Source Sans Pro`.
- Do not use fonts without Cyrillic glyphs.

## Rule 5 — Working habits

5.1. Before changing an existing file — read it first.

5.2. Follow the style, structure and naming of the surrounding code.

5.3. At the end, explain briefly what was done and where (with exact file paths).

5.4. Do not delete or overwrite someone else's work without explicit confirmation.

5.5. The inventory is the first source of knowledge. Before asking the user or
guessing about the project (machines, services, providers, models, keys, tools), check
it with `python3 tools/inventory.py`. If `data/inventory.db` is missing, create it with
`python3 tools/inventory.py init`.

## Rule 6 — No initiative and no action without permission

6.1. Before any action — running shell commands or scripts, reading or writing files,
changing configuration, running tests — the assistant waits for an explicit order from
the user.

6.2. If the message is a question, the assistant only answers. It does not perform
actions alongside the answer.

6.3. No initiative from the assistant. Nothing is executed unless explicitly requested.

6.4. An action is performed only after an explicit order. A clear sentence that
contains an action and "да" is both the order and the confirmation. A separate
confirmation is required only for irreversible actions: deleting files or data,
overwriting, `git push`, dropping a database.

6.5. An order for a task includes the reading necessary to execute it. Separate
permission is required only for actions outside the scope of the task.

6.6. When a message is ambiguous (question or order), the assistant treats it as a
question and asks. Ask only when the action or the "да" is missing, or when there is a
real risk.

## Rule 7 — Auto-discovery procedure

7.1. If a prompt needs ``secret.py`` or ``inventory.db`` and they are missing or
unusable, run the discovery script in the terminal before continuing.

7.2. Terminal procedure (run these exact commands):

   1. Open a terminal. On Windows, open **Git Bash**.
   2. Run:

      ``python3 tools/autodiscovery.py``

   3. Read the output:
      - If exit code is ``0`` and it says ``Minimum met``, proceed with the task.
      - If exit code is ``1``, install the missing tool it reports (git or bash).
      - If exit code is ``2``, the database is missing: run
        ``python3 tools/inventory.py init`` then repeat step 2.
      - If exit code is ``3``, the database is empty: run
        ``python3 tools/inventory.py init`` then repeat step 2.

7.3. ``autodiscovery.py`` checks: OS, processor, RAM, Python version, git,
bash (Git Bash on Windows), ``tools/secret.py``, ``tools/inventory.py``, and
whether ``data/inventory.db`` exists and has tables.

7.4. Minimum requirement: git bash + Python stdlib. GitHub token and email are
optional — you can work without them.

7.5. Exit codes: 0 OK, 1 minimum not met, 2 database missing, 3 database empty.
