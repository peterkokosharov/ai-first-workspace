# Review — design-document-v1 (deepseek-v4.1-flash-free)

## Summary

A disciplined draft that treats the folder itself as the product and the portability test as a first-class requirement (§6), which is the right framing. The inventory/secret split and the path-based key scheme are sound instincts. But v1 contradicts itself on the secret lifecycle and leaves out the machine-specific pieces that actually break "no file left behind" (§1).

## Strengths

- §1 and §6 define success as a runnable procedure, not a slogan; §6 adds explicit verification.
- §5.1's `provider/scope/kind` is the correct abstraction, and §5.3's "split on the first `|`" is the right parse rule. Rejecting duplicate paths is good hygiene.
- §5.4 reads `set` from stdin rather than argv, correctly keeping values out of shell history and `ps`.
- §11 non-goals actively cut scope, and §10 names over-engineering as a risk.
- §8 admits embarrassing defects (mode-664 token, mixed `~/SECRETS`) instead of hiding them — rare and useful.

## Weaknesses

1. **§5.2 vs §6 — the export has two contracts.** §5.2 says the file is temporary and "deleted after import"; §6 calls it "the backup of last resort" that "must be taken periodically." Both cannot hold. (Q1)
2. **§5.4's `auto` silently falls back to the plaintext file** when the native store is locked. That inverts §5.2's "native store is primary" and writes secrets to disk without consent. It is the worst default in the document. (Q4)
3. **§5.5 step 5 introduces a third format.** `secrets-import.txt` uses `KEY_PATH = value`, has no stated location, and would violate §11 if written inside the project. It also contradicts §5.3's claim that only one file ever holds values.
4. **§4 declares status a closed enum** (`active/planned/broken/retired`), yet §4.2 lists Facebook as "to clarify."
5. **§4.3 breaks its own convention:** `nemotron-3.5-super-vl-free` and `deepseek-chat` lack the `provider/` prefix every other row uses. §4.2 then reuses "provider" for services, so the word means two things.
6. **§3 contradicts itself on authority:** `INVENTORY.md` is both "planned" and "authoritative," while §8 says it will absorb `KEYS`/`MODELS.md`. Today, authority is undefined.
7. **§7 vs §5.5/§6:** rule 6 forbids any command without confirmation, yet the portability test is a command sequence. No clause says who authorizes verification.
8. **§5.6's "the tool does not decide policy" is false** — `auto` and `setup` choose the backend, which is policy.
9. **(Q3) Over-engineered:** five backends and macOS support for two machines (§4.1), a separate `probe` phase (§9 phase 0), and rule 6's absolute "no file read" clause, which would forbid the review loop §7 describes.

## Gaps

- **(Q2)** The archive lacks the agent's own configuration: §3 has no `opencode.json(c)` or `.opencode/` despite rule 3.4, and no `assets/fonts/` despite rule 4.2. "Open with the coding agent" (§1) is not reproducible from the folder alone. Provider logins/OAuth tokens live outside the project and are undeclared.
- Nothing scans the archive before shipping for accidental secrets. §6's checklist has no such gate, and §3's `.gitignore` excludes only `.tmp/`.
- §12 Q5 asks whether SSH/GPG keys are in scope, but §5.3's line-oriented format cannot hold a multi-line private key at all. That is a design limit, not an open question.
- **(Q6)** A path has 3+ segments, but Keychain, `secret-tool` and KWallet are all two-level (service+account, folder+entry). No mapping rule is given, so "the same string can be the target name" (§5.1) holds only for WCM. Path charset, surrounding whitespace and empty values are unspecified.
- §5.2 lists macOS and Windows backends with no corresponding machine in §4.1.
- No locking rule for `~/SECRETS`, no expiry/rotation metadata, no integrity check, no defined transfer channel for the export.
- §8's 664 token and mixed `~/SECRETS` are logged but absent from §9's roadmap; the "collect every secret into one list" step (§9 phase 0.5) centralizes all credentials with no stated location or destruction step.

## Recommendations

1. **(Q5)** Settle the export lifecycle first: one file, one format, one location, defined retention. Make `auto` refuse to write plaintext unless `--backend file` is passed explicitly.
2. Specify the path→per-backend mapping and a path charset, and test both before writing any backend code.
3. Add an archive pre-flight (secret scan plus required-files check), and put `opencode.json`/`.opencode/` and fonts into §3.
4. Resolve §12 Q5 now; if SSH/GPG keys are out of scope, say so in §11.
5. Fix the enum, the provider-prefix, and the "authoritative" inconsistencies, then fold phase 0.5 into a defined, shredded-after-use step.
6. Defer macOS/Keychain until a third machine actually exists.

## Verdict

**6/10** — a well-shaped v1 whose core abstraction is right, but the contradictory secret lifecycle and the missing agent configuration would break the very portability test it defines.
