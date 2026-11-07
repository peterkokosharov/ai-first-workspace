# Review: Design Document v1 — Portable Development Workspace

**Reviewer:** iceman-free (independent external review)  
**Date:** 2026-11-07

## Summary
The document defines a clear, portable workspace for AI-assisted development with strong behavioral governance (Rule 6, §2) and a pragmatic secret-management sketch (§5). It is largely coherent, but several portability and operational details remain underspecified, and a few areas risk complexity disproportionate to a small personal workspace.

## Strengths
- **Clear purpose and success test.** §1 states the archive→move→unpack→continue criterion; §6 reinforces it as a design requirement, not an afterthought.
- **Governance is explicit.** Rule 6 (§2) and the review loop (§7) create a useful control surface for AI-assisted work.
- **Secret naming is sensible.** The `provider/scope/kind` path scheme (§5.1) avoids collisions and maps reasonably to native stores (§5.2).
- **Honest current-state inventory.** §8 lists concrete issues (placeholder DeepSeek key, `~/github_token` permissions, mixed `~/SECRETS` content), which supports actionable follow-up.

## Weaknesses
- **Internal consistency gaps.** §3 lists `INVENTORY.md` and `README.md` as planned, but §1/§6 imply the portability flow depends on documented recovery steps; the document does not state the minimum viable state required before claiming the §1 criterion. §8 notes `KEYS`/`MODELS.md` duplication and mixed `~/SECRETS`, conflicting with §5.3/§5.6 until cleaned.
- **Portability depends on unstated prerequisites.** §6 says “run `secret.py setup`” and verify tests, but §3/§9 show `tools/secret.py` and `tests/` are planned. The recovery path is circular until Phase 1 (§9) exists.
- **Backend behavior is under-specified.** §5.2 lists KWallet via DCOP and a 3-second timeout (§10), but does not define unlock prompts, headless failure modes, or how `auto` chooses between native store and file when a store exists but is locked/unavailable.
- **Operational ambiguity.** §4.1/§4.3 include “to verify”/provider-specific details; §12 leaves key questions open (wallet name, overwrite confirmation, backup cadence, SSH/GPG scope) that affect implementation and security.

## Gaps
- **No concrete archive/restore procedure.** Missing: what to include/exclude (`.tmp/`, `.git/`, local caches), checksum/verification step, and how to handle line endings/permissions across Linux/Windows (§4.1, §6).
- **No secret lifecycle/rotation policy.** §5 covers storage/transfer but not rotation, revocation, compromise response, or audit of where a key was used.
- **No test/acceptance definition.** §6 mentions “tests pass” but no test plan, fixtures, or mocked-backend contract for `probe`/`setup` (§5.4, §9).

## Recommendations
1. **Define a minimum portable baseline** (§1, §3, §6): require `README.md`, `INVENTORY.md` (or explicit interim source), and a working `secret.py` before claiming the success criterion; document exact archive contents.
2. **Specify `secret.py` semantics** (§5.4, §5.5, §10): `auto` decision table, locked-store behavior, overwrite confirmation (§12.2), `--json` schema for `list`, and deterministic exit codes/error messages.
3. **Add a security hardening pass** (§5.3, §5.6, §8): fix `~/github_token` permissions, forbid placeholder values in active entries, define export retention/deletion, and document compromise/rotation steps.
4. **Defer complexity** (§5.2, §9): implement file backend + clear export/import first; add KWallet/Keychain/WCM only after probe results and real need.

## Verdict
**7/10** — A solid, honest foundation with clear goals and governance, but it needs tighter operational definitions and a completed baseline toolchain to reliably meet its portability promise.