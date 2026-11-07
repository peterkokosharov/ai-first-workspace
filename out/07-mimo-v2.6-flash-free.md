# Review — design-document-v1 (mimo-v2.6-flash-free)

## Summary

The document specifies a portable, self-contained workspace: six behavioural rules, an
inventory of machines/services/models (§4), and a `secret.py` with hierarchical key
paths, several backends and a temporary plaintext export (§5). The intent and
boundaries are unusually clear, but the spec contradicts itself in places (Q1: mostly
consistent, with real faults), leaves the portability recipe unspecified (Q2), and its
secret manager has a broken Windows retrieval path plus an unaddressed backup/transfer
risk (Q4, Q6).

## Strengths

- Honest scoping: non-goals (§11), named risks (§10) and open questions (§12) are
  concrete, not decorative.
- The key path scheme (§5.1) is a genuinely better replacement for flat names —
  collision-free, schema-stable, reusable as a native-store target name.
- `set` reads from stdin, writes are atomic with `chmod 600`, and the export parser
  splits on the first `|` (§5.3–5.4) — real thought about argv/history leaks and
  values containing separators.
- Exit codes and a `probe` that never touches real secrets (§5.4) are proper CLI
  hygiene.
- The portability test is a numbered procedure (§6), not a slogan.
- §8's known issues (`~/github_token` at mode `664`, `~/SECRETS` polluted with a model
  table) are candid about live problems.

## Weaknesses (Q1, Q3, Q4)

1. **Status vocabulary violated.** §4 defines `active/planned/broken/retired`; §4.2
   marks Facebook `to clarify`.
2. **Two export formats.** §5.3 specifies `KEY_PATH | value`; §5.5 writes
   `secrets-import.txt` as `KEY_PATH = value`. §5.5 never says that file is deleted or
   mode-protected, yet §5.3 claims `~/SECRETS` is "the only file that ever contains
   values".
3. **Verification impossible as written.** §6 step 6 requires `get` to return values,
   but the archive carries none (§6, §5.5 step 4). The step silently presumes a
   separately transferred export that is never listed as a precondition.
4. **Dangling references.** `big-pickle` (§10) appears in no model table (§4.3), and
   the glossary entry "Stealth model" (§13) is never used in the document.
5. **`auto` undermines the policy.** §5.4's default silently falls back to the plaintext
   file when a store is locked (§10), contradicting "native store is primary" (§5.2),
   with no warning or required flag.
6. **Over-engineering (Q3).** Four native backends (§5.2) serve two existing machines
   (§4.1) — macOS and GNOME Keyring target hardware nobody owns. Multi-level
   `work/prj1` scopes (§5.1) exist for credentials that may not exist at all (§12.3).
   `--json` output and the phase 0/2 DCOP probing (§9) are heavy machinery for the 7
   keys counted in §8.
7. **Windows is broken (Q4/Q6).** `cmdkey` can add and delete generic credentials but
   cannot read a value back, so `secret.py get` (§5.4) has no retrieval path on
   `win10` (§4.1). Separately, `chmod 600` (§5.3, §5.6 "always 600") is a no-op on
   NTFS — a stated security property that silently fails on the secondary machine.

## Gaps (Q2, Q4)

- **No archive recipe.** Nothing says whether `in/`, `out/`, `.tmp/` and `.gitignore`
  travel, and no check verifies the §1 success criterion ("no file left behind").
- **Asserted but absent resources.** Rule 4 requires bundled fonts and restorable
  dependencies (§2), yet §3 has no `assets/fonts/` and §4.4 lists no package manager or
  lockfile.
- **Backup is undefined.** §6 requires periodic exports but not their location,
  encryption, or retention (deferred to §12.6) — i.e. plaintext copies accumulating
  somewhere with no stated protection.
- **Unaddressed security risk (Q4).** Transfer/backup of plaintext exports plus the
  undeleted `secrets-import.txt` (§5.5), compounded by `get` and `export --out -`
  writing values to stdout (§5.4) which lands in session history stored *outside* the
  project (§6) — no rule covers captured output, only actions.
- No rotation/revocation guidance and no integrity check (checksum) on a transferred
  export.

## Recommendations (Q5, priority order)

1. Fix Windows retrieval (Win32 `CredRead`/DPAPI, or declare `wcm` write-only) and
   remove the false "always 600" claim for NTFS.
2. Unify on one export format; specify `secrets-import.txt` deletion and mode; decide
   backup location and encryption now, not as an open question.
3. Make the `auto`→file fallback loud (require `--allow-file`).
4. Write the archive recipe and actually run the §6 test once before v2.
5. Drop the macOS and GNOME backends until such a machine exists — §10's own rule:
   features only on real need.
6. Repair the status vocabulary and the `big-pickle`/stealth dangling references.

## Verdict

**6/10** — a candid, well-bounded design whose key-path and export ideas are sound,
but which fails its own portability test on Windows retrieval, backup handling, and an
unwritten archive recipe.
