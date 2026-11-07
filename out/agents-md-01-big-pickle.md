# Review of `AGENTS.md` — subagent 01 (big-pickle)

## 1. Understanding

1. **Rule 1 — Language of communication.** The user writes Bulgarian in Latin letters ("paydzhin"); this is normal and must not be corrected or commented on. The assistant answers in literary Bulgarian, in Cyrillic, with correct spelling and punctuation. File names, commands, code and technical terms stay in their original Latin form where precision requires it.
2. **Rule 2 — Records.** All written records (notes, documentation, journals, task lists, explanations) are kept in Bulgarian and in Markdown only — no `.txt` or other formats. This also applies to `AGENTS.md` itself.
3. **Rule 3 — Everything stays in this folder.** The folder is self-contained and portable: archive it, move it to another machine, unpack, open with OpenCode, and work continues. Nothing belonging to the project is scattered elsewhere on disk (no home-directory files, no global config, no system-directory changes). The ban covers disk files only, not network uploads. All paths are relative to the folder root. OpenCode configuration for the project is local (`opencode.json(c)` or `.opencode/`). Fonts and resources live in the folder. Dependencies are local or restorable from a lockfile. Temporary files go in `.tmp/`. `README.md` is the entry point. Secrets never enter the archive or git: values live in `~/SECRETS` (`KEY_NAME | service | value`), while only `KEYS` (names plus the path to `~/SECRETS`, no values) stays in the folder. A portability test (archive → transfer → unpack → open) is defined. Only OpenCode itself, `~/SECRETS`, session history and system packages remain outside the project.
4. **Rule 4 — Technical requirements.** All files are UTF-8. Only fonts shipped with the project and having full Cyrillic support are used (DejaVu Sans, Noto Sans, Liberation Sans, Fira Sans, Roboto, Source Sans Pro preferred); fonts without Cyrillic glyphs are forbidden.
5. **Rule 5 — Working habits.** Read an existing file before changing it. Match the style, structure and naming of the surrounding code. At the end, briefly explain what was done and where, with exact file paths. Do not delete or overwrite someone else's work without explicit confirmation.
6. **Rule 6 — No initiative, no action without permission.** Before any action — shell commands or scripts, reading or writing files, config changes, tests — the assistant waits for an explicit order. If the message is a question, only answer it. No initiative; nothing is done unless explicitly requested. An action requires both an explicit order and a "yes" confirmation. When in doubt whether a message is a question or an order, treat it as a question and ask.

## 2. Obligations and prohibitions

**Must:** answer in Cyrillic Bulgarian; write every record in Bulgarian `.md`; keep all project artefacts inside the folder; use relative paths; keep OpenCode config local; ship fonts and resources in the folder; keep temp files in `.tmp/`; maintain `README.md`; keep secret values only in `~/SECRETS` with only `KEYS` in the project; write UTF-8; use Cyrillic-capable bundled fonts; read before editing; follow local style; report what changed and where; confirm before overwriting others' work; wait for explicit permission; ask when ambiguous.

**Must not:** correct or comment on the user's transliterated Bulgarian; use `.txt` or other record formats; write project files to home/system paths; use absolute or machine-specific paths; rely on global OpenCode config or system fonts; install globally or modify the system; put secret values in the project, archive or git; delete or overwrite foreign work without confirmation; act on a question or on an ambiguous message.

## 3. Ambiguities

- **3.3 vs 3.9:** 3.3 forbids absolute paths, yet 3.9 mandates `~/SECRETS`, an absolute home path — a direct contradiction with no stated exception.
- **3.1 vs 3.9/3.11:** 3.1 says nothing outside the folder, while 3.9 and 3.11 place `~/SECRETS` outside. It is an implicit exception, not declared as one.
- **6.1 vs 5.1:** 6.1 requires explicit permission even to *read* files, but 5.1 requires reading before editing. Does one permission cover the whole task, or every single read?
- **6.4 vs 6.1:** 6.1 requires an explicit order; 6.4 additionally requires a "yes" confirmation. Whether a single command containing "yes" suffices is unclear.
- **2.2 scope:** "All records" in `.md` only — unclear whether code, `opencode.json`, lockfiles and `KEYS` (extensionless, see 3.9) are exempt.
- **6.5:** "When in doubt" is undefined; almost any real request could be reclassified as a question, enabling paralysis.
- **1.2 vs this task:** the instruction to answer in English directly contradicts 1.2; the rulebook does not say which wins.
- **3.10:** unclear whether the portability test is mandatory after every change or only on demand.

## 4. First action

Per 6.1 I would not touch anything before an explicit order. On receiving one, I would read `README.md` (3.8) — it is the designated entry point and tells me what the project is and how to continue — then read `KEYS` to know which secrets exist, without opening `~/SECRETS` unless required.

## 5. Verdict

**No** — several clauses (3.3 vs 3.9, 6.1 vs 5.1, 6.4 vs 6.1) contradict each other or leave permission granularity undefined, so clarification is needed before acting.
