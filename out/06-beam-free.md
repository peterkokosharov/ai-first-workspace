# Review — design-document-v1.md (beam-free)

## Summary

The design proposes a self-contained, portable workspace for AI-assisted development, built around Markdown inventories and a Python secret manager with hierarchical key paths and pluggable OS backends. It is unusually honest about scope and open questions, but several internal inconsistencies and unspecified transfer/security details keep it from being implementation-ready.

## Strengths

- Clear purpose and an explicit, testable success criterion (§1).
- Honest non-goals (§11) and a real risk list (§10) show scope discipline.
- The `provider/scope/kind` key-path scheme avoids collisions and scales to projects (§5.1).
- Native-store-primary with a temporary export aligns with the portability goal (§5.2).
- Atomic writes, mode 600, and stdin-based `set` reduce leakage (§5.3, §5.4, §5.6).
- Portability is treated as an explicit test, not an afterthought (§6).

## Weaknesses

- Inconsistent export format: `|` separator in §5.3 versus `=` in §5.5 (`secrets-import.txt`). Two formats for the same data.
- `secrets-import.txt` location is unspecified; if written inside the project it violates §11 and §3.
- `MODELS.md` is called authoritative (§7) yet "to be merged into `INVENTORY.md`" (§8) — two sources of truth persist.
- Key-path grammar has no minimum-segment rule or validation; Windows Credential Manager target-name limits (length/characters) are not considered (§5.1).
- KWallet/DCOP probing on obscure TDE is over-engineering for two personal machines (§5.2, §9).
- `get` prints a secret to stdout with no caution, leaking via logs/scrollback (§5.4).
- "mode 600" is Unix-only; Windows ACLs for the export file are unspecified (§5.3, §5.6).

## Gaps

- No lockfile or dependency spec in the layout (§3) despite the self-containment principle.
- No `assets/fonts/` directory in the layout (§3) although bundled Cyrillic fonts are required (§4, Rule 4).
- No secure transfer mechanism for the export between machines (§6).
- No accidental-commit guard beyond excluding `.tmp/` (§3, §7).
- No rotation/expiry policy; SSH/GPG scope and backup cadence left as open questions (§12).
- No migration steps from `KEYS`/`MODELS.md` to `INVENTORY.md` (§8).
- No verification that `list` output matches the inventory's expected key set (§4, §5.4).

## Recommendations

1. Reconcile the export format and pin `secrets-import.txt` outside the project with auto-delete and a specified secure transfer channel (§5.3, §5.5).
2. Define key-path validation and WCM constraints, including the two-segment case (§5.1).
3. Merge `KEYS` and `MODELS.md` into `INVENTORY.md` first to restore a single source of truth (§7, §8).
4. Add a lockfile, a fonts directory, and an OpenCode/Python version pin to the layout and portability test (§3, §6).
5. Defer or drop the KWallet backend; keep the file backend plus one mainstream store (§5.2, §9).
6. Extend `.gitignore` for secret files and add a pre-commit check (§3, §7).

## Verdict

6 — solid intent and honest scoping, but unresolved format inconsistencies and unspecified transfer/security details make it not yet implementation-ready.
