# Review of `AGENTS.md` — Nemotron 3 Ultra

## 1. Understanding

1. **Communication language**: The user writes in "pajdin" (phonetic Cyrillic with Latin letters, e.g., `zdr. haide da suzdadem agents.md`). This is normal and must not be corrected or commented on. The assistant must reply in standard literary Bulgarian using Cyrillic script — proper grammar, punctuation, capitalization. Technical terms, filenames, commands, and code stay in their original Latin form when needed for precision.

2. **Records/notes**: All records (notes, documentation, journals, task lists, explanations) are kept in Bulgarian only, in Markdown (`.md`) format exclusively. This applies to `AGENTS.md` itself as well.

3. **Self-contained folder (portability)**: The project folder is self-contained and portable — archive, move to another machine, unzip, open with OpenCode, and work continues without missing parts.
   - 3.1: Nothing scatters outside the folder on disk. No files in home directory, no global config, no system directory changes.
   - 3.2: The 3.1 ban is disk-only; uploading data to the internet is allowed when the task requires it.
   - 3.3: All paths are relative to the folder root. No absolute or machine-dependent paths.
   - 3.4: OpenCode config for the project is local — in `opencode.json(c)` or `.opencode/` (agents, commands, skills, permissions, plugins). No reliance on global config.
   - 3.5: Fonts and assets live in the folder (e.g., `assets/fonts/`). No reliance on system fonts.
   - 3.6: Dependencies are local or restorable from lockfile. No global installs, no system changes.
   - 3.7: Temporary files go in `.tmp/` inside the folder and are not needed to continue work.
   - 3.8: Entry point: `README.md` at root briefly describes the project and how to continue work.
   - 3.9: Secrets never enter the archive or git. Values stay outside the project in `~/SECRETS` with format `KEY_NAME | service | value`. The folder keeps only `KEYS` — names of secrets and the path to `~/SECRETS`, no values. On another machine, `~/SECRETS` is recreated.
   - 3.10: Portability test: archive → transfer → unzip → open with OpenCode → work continues.
   - 3.11: Outside the folder remain only: the OpenCode program itself, `~/SECRETS`, session history, and system packages. These are set up once per new machine and are not part of the project.

4. **Technical requirements**:
   - 4.1: All files encoded in UTF-8.
   - 4.2: Only fonts with full Cyrillic support, delivered with the project (see 3.5). Preferred: DejaVu Sans, Noto Sans, Liberation Sans, Fira Sans, Roboto, Source Sans Pro. No fonts lacking Cyrillic glyphs.

5. **Work habits**:
   - 5.1: Before changing an existing file, read it first.
   - 5.2: Follow the style, structure, and naming of surrounding code.
   - 5.3: At the end, briefly explain what was done and where (with exact file paths).
   - 5.4: Foreign work is not deleted or overwritten without explicit confirmation.

6. **No initiative, no action without permission**:
   - 6.1: Before any action — running bash commands/scripts, reading/writing files, config changes, tests — the assistant waits for an explicit user command.
   - 6.2: If the message is a question, the assistant only answers. No actions alongside the answer.
   - 6.3: No initiative from the assistant. Nothing executes unless explicitly asked.
   - 6.4: Action executes only after explicit command and confirmation "yes".
   - 6.5: On ambiguity (question vs command), the assistant treats it as a question and asks, rather than acting.

---

## 2. Obligations and Prohibitions

**Must do:**
- Reply in literary Bulgarian, Cyrillic script, correct grammar/punctuation/capitalization.
- Keep technical terms, filenames, commands, code in original Latin form when precision requires.
- Write all records (notes, docs, journals, tasks, explanations) in Bulgarian, Markdown (`.md`) only.
- Keep everything inside the project folder: code, config, fonts, assets, dependencies (local or lockfile-restorable), temp files in `.tmp/`.
- Use relative paths only (relative to folder root).
- Store OpenCode config locally in `opencode.json(c)` or `.opencode/`.
- Encode all files as UTF-8.
- Use only project-bundled fonts with full Cyrillic support (preferred list given).
- Read existing files before modifying them.
- Match surrounding code style, structure, naming.
- After work, briefly summarize what was done with exact file paths.
- Get explicit confirmation before deleting/overwriting foreign work.
- Wait for explicit user command before any action (bash, read/write files, config changes, tests).
- Treat ambiguous messages as questions and ask for clarification.
- Execute actions only after explicit command + "yes" confirmation.
- Keep secrets out of archive/git: values in `~/SECRETS` (format `KEY_NAME | service | value`), only `KEYS` (names + path to `~/SECRETS`) in project.
- Maintain `README.md` at root as entry point.

**Must not do:**
- Correct or comment on user's "pajdin" writing.
- Use Latin script/transliteration in replies (except technical terms, filenames, commands, code).
- Write records in any language other than Bulgarian.
- Use formats other than `.md` for records.
- Scatter project files outside the folder (home dir, global config, system dirs).
- Use absolute or machine-dependent paths.
- Rely on global OpenCode config.
- Rely on system fonts.
- Use global dependency installs or modify system.
- Leave temp files outside `.tmp/` or make them required for continuity.
- Put secret values in archive/git or in the project folder.
- Use fonts lacking Cyrillic glyphs.
- Modify existing files without reading them first.
- Delete/overwrite foreign work without explicit confirmation.
- Take any initiative or act without explicit user command.
- Perform actions while answering a question.
- Act on ambiguous input without clarifying first.

---

## 3. Ambiguities

**Rule 1.2 / Rule 2.1 tension**: Rule 1.2 says "termini, imena na failove, komandi i kod ostavat v originalniya im vid (latinitsa), kogato tova e nujno za tochnost" — but Rule 2.1 says "Vsički zapisi se vodiat na edin ezik — balgarski." If a record (Markdown doc) contains a code snippet or command, is that a violation of 2.1? The exception in 1.2 covers "when needed for precision," but 2.1 has no such qualifier. Contradiction: 2.1 appears to forbid Latin entirely in records, while 1.2 permits it for technical precision.

**Rule 3.9 ambiguity**: "V papkata stoit samo `KEYS` — imenata na tainite i pŭtʹ do `~/SECRETS`, bez stoinosti." Does `KEYS` refer to a specific filename (e.g., `KEYS` or `KEYS.md`) or a conceptual list? No filename or format specified. Also: "Na drugata mashina `~/SECRETS` se sŭzdava nanovo" — but who creates it? The assistant? The user? No procedure described.

**Rule 3.11**: "Izven papkata ostavat samo: samata programa OpenCode, failŭt `~/SECRETS`, istoriata na sesiite i sistemnite paketi." Session history is outside the folder — but Rule 3.10's portability test says "otvori ya s OpenCode → rabota prodŭlzhava." If session history is external and not part of the project, how does work "continue" seamlessly? Contradiction between "portable, self-contained" and "session history stays outside."

**Rule 6.1 vs 6.4**: 6.1 says "chaka izrichna zapoved ot potrebitelya." 6.4 says "deystvie se izvŭrshva samo sled izrichna zapoved i potvŭrzhdenie 'da'." Is "da" a separate confirmation step after the command, or is the command itself the confirmation? Unclear whether two-step (command → assistant asks "da?" → user says "da" → act) or one-step (user says "da, napravi X" → act).

**Rule
