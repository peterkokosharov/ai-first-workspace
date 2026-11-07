# Design Document v1 — External Review (flint-40b-free)

## Summary

The document presents a portable, self-contained AI development workspace, progressing from purpose (§1) through the six governing rules (§2), repository layout (§3), inventory (§4), secret management (§5), portability (§6), governance (§7), current state (§8), roadmap (§9), risks (§10), non-goals (§11) and open questions (§12). The ambition and self-awareness behind it are genuine, but the document contains internal contradictions and leaves key procedures underspecified, so it cannot yet serve as an executable design.

## Strengths

- The success criterion of §1 is concrete and operational: archive → move → unpack → open with the agent → continue, with nothing left behind.
- The key path scheme of §5.1 (`provider/scope/kind`) is simple, collision-free and migration-friendly; its rationale is clearly argued.
- The security posture is proportionate: native store primary with temporary export fallback (§5.2), atomic writes with mode `600` (§5.3, §5.6), `set` reading from stdin to protect against shell history (§5.4). The tool deliberately avoids policy decisions (§5.6).

## Weaknesses

- **Contradiction (§5.3 vs §5.5):** the export file format is defined as `KEY_PATH | value` split on the first `|`, but §5.5 step 5 describes the fallback import file using `KEY_PATH = value` lines. The formats are incompatible; at least one is wrong.
- **Stale layout (§3):** the tree still lists `KEYS` and `MODELS.md` as live artifacts, while §8 and the roadmap describe their migration into `INVENTORY.md`. The layout was not updated with that migration.
- **Unimplementable prompt (§5.5):** "no credential store found — create one?" is framed as a question, but the CLI contract in §5.4 defines no interactive behaviour, which an unattended coding agent cannot satisfy.

## Gaps

- **Portability procedure (§6):** the steps lack an archive manifest, checksums, source-machine cleanup and a rule for how the agent identifies its machine; per-machine values (users, sudo setups) are never wired into the workflow.
- **Open questions (§12):** six questions remain open (KWallet wallet name, overwrite confirmation, work credentials, Python version, SSH/GPG scope, export frequency), leaving the end-to-end verification procedure of §6 untestable.

## Answers to the six questions

1. **Is the design internally consistent?** Mostly yes, but the §5.3/§5.5 export delimiter conflict is a concrete, unresolved error; the §3 layout also lags behind the §8 migration notes.
2. **What is missing for the portability goal?** Machine detection, archive content specification, post-unpack verification and source-machine cleanup are missing (§6).
3. **Where is it over-engineered?** The design stays close to minimal, but the broad backend/fallback matrix (§5.2) and phase-0 KWallet probing (§9) may exceed the stated small scope.
4. **Which security risk is not addressed?** The risk that the coding agent itself reads secrets (via `get`, logs, process listing) has no threat model; unlock policy and audit logging are absent.
5. **What would you change first?** Resolve the export-format contradiction and write the missing `README.md` (§3, §8).
6. **Is the secret-manager design sound?** The path scheme and native-primary design are sound (§5.1–§5.6); the export format bug and undefined locked-store fallback reduce confidence.

## Recommendations

1. Resolve and regression-test the export-file format (§5.3, §5.5).
2. Specify machine detection and archive lifecycle (§6).
3. Close or time-box the open questions (§12).

## Verdict

**6/10** — the core design and honest known issues are strong, but the export-format defect and portability gaps must be fixed before the design can be executed.
