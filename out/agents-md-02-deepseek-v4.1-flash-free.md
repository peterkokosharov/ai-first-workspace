# Review of `AGENTS.md` — DeepSeek V4.1 Flash Free

## 1. Understanding

1. **Language (Rule 1).** The user may write Bulgarian in Latin letters (phonetic "pigeon"); this is accepted without correction or comment (1.1). The assistant answers in literary Bulgarian Cyrillic with correct grammar, punctuation and capitalisation, keeping technical terms, file names, commands and code in Latin where accuracy requires it (1.2).
2. **Records (Rule 2).** Notes, documentation, diaries, task lists and explanations are in Bulgarian (2.1) and stored as `.md`, never `.txt` or another format (2.2); this applies to `AGENTS.md` too (2.3).
3. **Self-containment (Rule 3).** Everything project-related stays in the folder — no home-directory files, global configuration or system changes (3.1). The ban covers disk files, not network uploads, allowed when the task needs them (3.2). Paths are relative to the root (3.3). OpenCode config is local in `opencode.json(c)` or `.opencode/` (3.4). Fonts and assets live in the folder, e.g. `assets/fonts/`, not system fonts (3.5). Dependencies are local or lockfile-restorable, with no global installs (3.6). Temp files go in `.tmp/` (3.7). `README.md` is the entry point (3.8). Secrets stay out of the archive and git; values live in `~/SECRETS` as `KEY_NAME | service | value`, while the folder holds only `KEYS` with names and the path (3.9). Portability is tested by archive → transfer → unpack → open in OpenCode → continue (3.10). Only OpenCode, `~/SECRETS`, session history and system packages remain outside (3.11).
4. **Technical (Rule 4).** All files are UTF-8 (4.1). Only bundled fonts with full Cyrillic support are used — preferred DejaVu Sans, Noto Sans, Liberation Sans, Fira Sans, Roboto, Source Sans Pro; fonts without Cyrillic glyphs are forbidden (4.2).
5. **Work habits (Rule 5).** Read a file before changing it (5.1). Follow surrounding style, structure and naming (5.2). At the end, explain briefly what was done and where, with exact paths (5.3). Never delete or overwrite others' work without explicit confirmation (5.4).
6. **No initiative (Rule 6).** Wait for an explicit order before any action: bash commands, scripts, reading or writing files, configuration changes, tests (6.1). A question gets an answer only, with no side actions (6.2). Perform nothing unrequested (6.3). Act only after an explicit order plus a "да" (6.4). Treat ambiguity as a question and ask rather than act (6.5).

## 2. Obligations and prohibitions

**Must:** answer in Bulgarian Cyrillic; keep records Bulgarian `.md`; keep everything inside the folder with relative paths; keep config, fonts and dependencies local; use `.tmp/`; maintain `README.md`; keep secrets only in `~/SECRETS`; write UTF-8 with Cyrillic fonts; read before editing; match style; report exact paths; confirm destructive changes; await an order and "да".

**Must not:** correct transliteration; create `.txt`; write outside the folder or use absolute paths; rely on global config, fonts or installs; expose secrets in the folder, archive or git; overwrite others' work unconfirmed; act on questions, ambiguity or unrequested work.

## 3. Ambiguities

- **2.2:** "Всички записи се правят във формат `.md`" reads as covering all records, yet the project also contains code, fonts, JSON config and lockfiles; 2.1 limits this to notes and documentation, but 2.2 does not.
- **3.3 vs 3.9:** 3.3 forbids absolute paths, while 3.9 mandates `~/SECRETS`, a home path outside the folder. 3.11 permits the exception but never reconciles it with 3.3.
- **6.1 vs 5.1:** 6.1 requires an order even to read a file, while 5.1 requires reading before editing; whether the same order covers reading is unstated.
- **6.4:** "само след изрична заповед и потвърждение „да“" implies a separate confirmation per action, which would make multi-step work impossible; unclear whether one "да" authorises the whole task.
- **3.2 vs 3.9:** 3.2 permits internet uploads when required but never excludes secrets from that permission — a risky gap.

## 4. First action

Under 6.1 I would take no action, not even exploratory reads, until given an explicit order. Once ordered to work, I would read `README.md` and list the root — the documented entry point (3.8) and the minimum needed to orient myself. Here I was restricted to `AGENTS.md`, so I read only that.

## 5. Verdict

**No** — 2.2, 3.3/3.9 and 6.4 conflict or overreach, so a careful assistant must ask before acting.
