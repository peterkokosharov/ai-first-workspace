# Review — design-document-v1 (big-pickle)

## Summary

The document specifies a portable, self-contained workspace centred on a small credential
manager and an inventory of two machines. It is unusually honest about current state (§8)
and non-goals (§11), and the key-path scheme (§5.1) is genuinely good. The weaknesses sit
in the secret tool's fallback paths, which contradict each other, and in a layout that
omits the files making the folder portable.

## Strengths

- §5.1: path-based identity outlives flat names, maps onto Windows Credential Manager
  targets, and absorbs new projects without a schema change.
- §5.4: values from stdin rather than argv, enumerated exit codes, `list` never prints
  values. The right defaults.
- §5.3: split on the first `|`, duplicate paths are an error, atomic `os.replace` plus
  `chmod 600` — specified tightly enough to be tested.
- §8: naming the placeholder key, the `664` token and the DCOP unknowns beats a cleaned-up
  status page.
- §9 decouples phase 1 from phase 0: the critical path is honest.

## Weaknesses

**Q1 — internal consistency: no, and the worst break is in the secret tool.**

- §5.5 step 5 contradicts §5.3. The fallback writes `secrets-import.txt` with
  `KEY_PATH = value` lines — a second format (`=`, not `|`), a second filename, a `.txt`
  extension that violates the Markdown-only record rule, and no stated location or mode.
  A plaintext values file, plausibly inside the project, is what §2.3 and §5.3 forbid.
- §5.4's default `auto` ("native store if available and unlocked, otherwise file")
  silently chooses the *write* destination. With KWallet locked at login, `set` writes to
  the file while `get` reads the store — exactly the "two sources of truth" risk §10 says
  must never happen. §5.6 claims "the tool does not decide policy"; §5.4 makes it decide
  the most policy-laden thing in the design.
- §8 arithmetic: "6 real API keys + 1 GitHub token", but the deepseek key is a placeholder —
  five real API keys.
- §4.3 gives `nemotron-3.5-super-vl-free` no provider prefix, unlike every other model;
  §4.2 omits `kiko-proxy`/LiteLLM although §8 and §11 treat them as live.
- §12 defers decisions the design should make: overwrite confirmation (2) and SSH/GPG
  scope (5). Open scope weakens §11.

**Q3 — over-engineering.** Five backends across four OS families (§5.2) serve two machines,
one of them Q4OS/TDE; the macOS and GNOME/Mint backends are never exercised. Seven keys do
not need `export`/`import`/`setup`/`probe`, four exit codes, `--json`, and variable-depth
scopes. §10 warns about over-engineering, then §5.2 and §5.4 do it anyway.

**Q4 — the unaddressed security risk.** The export is plaintext at mode `600`, with no
encryption, transport story or integrity check; §6 mandates periodic exports without
saying how one crosses machines safely. §1 promises to say *who may read* secrets, but §5
defines no access policy, while rule 6 makes the agent an actor with shell access.

## Gaps

**Q2 — what portability still needs.**

- §3 lists no `assets/fonts/`, no `.opencode/`, and no lockfile, although rules 3.4, 3.5
  and 3.6 require all three. As drawn, the §3.10 test cannot pass.
- §6 is a six-step narrative, not a procedure: no archive command, exclusion list,
  checksum or manifest of what must be recreated. It cannot be run twice identically.
- `probe` (§5.4) is undefined — dummy write, read, delete? The duplicate-path error of
  §5.3 maps to no exit code.
- §6 step 6 says "tests pass", but §3 marks `tests/` as planned — circular verification.
- No Windows specifics: `~/SECRETS` line endings, `cmdkey` acceptance of the path scheme,
  name-length limits.
- No rotation or revocation path; §8's world-readable GitHub token has no owner in §9.

## Recommendations

**Q5 — in order.**

1. Fix §5.5 step 5: one format (`|`), file outside the project, mode `600`, explicit
   name, deletion on failure too.
2. Delete implicit write-fallback from §5.4. Writes go to the selected backend or fail;
   file writes only under an explicit `--backend file`, with a warning.
3. Consolidate `KEYS` and `MODELS.md` into one `INVENTORY.md` schema before phase 1, and
   drop placeholder rows that carry no account or key.
4. Add `assets/fonts/`, `.opencode/`, a lockfile and a checksummed archive script to §3;
   run the portability test once and record it.
5. Decide §12.2 and §12.5, and assign each §8 known issue to a roadmap phase.
6. Cut macOS/Mint backends and `export`/`import`/`probe` from phases 1–2 until a real
   machine needs them.

**Q6 — is the secret-manager design sound?** The core is: path names, native store primary,
export as a temporary artifact. It is unsound in two places — the undocumented second
fallback format (§5.5) and the write-fallback that creates the dual-source state §10
forbids. Fix those and the concept holds.

## Verdict

**6/10** — a good skeleton with one strong idea (key paths) undermined by contradictory
fallback behaviour and a layout that omits the files portability actually depends on.
