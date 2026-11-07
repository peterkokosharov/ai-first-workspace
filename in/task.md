# Review task — design document v1

You are reviewing a design document for a portable development workspace.

## What to read

- `in/design-document-v1.md` — the document under review.

Do **not** read `in/design-runtime-v1.md`. It is excluded from this round.

## Context

The project is a self-contained folder for AI-assisted software development. It holds
rules, an inventory of machines/services/models/keys/tools, and a small secret manager.
It must survive being archived and moved to another machine. The author is a software
developer who wants honest, specific criticism, not praise.

## What to produce

Exactly one file, in English, following the naming given by the caller:

```
out/<NN>-<model>.md
```

Maximum 800 words. Use these sections:

1. **Summary** — 2–3 sentences.
2. **Strengths** — what is genuinely good.
3. **Weaknesses** — concrete problems.
4. **Gaps** — what is missing or underspecified.
5. **Recommendations** — what to change first, in priority order.
6. **Verdict** — one number from 1 to 10, plus one sentence.

## Rules

- Critique, do not rewrite the document.
- Cite section numbers (for example "§5.4").
- Be specific; no generic advice.
- Do not read `~/SECRETS` or any file containing secret values.
- Do not run commands that print secrets.
- Do not modify anything in `in/`.
- Write only your own file in `out/`.

## Questions to answer

1. Is the design internally consistent?
2. What is missing for the portability goal?
3. Where is it over-engineered for its stated purpose?
4. Which security risk is not addressed?
5. What would you change first?
6. Is the secret-manager design (path names, native store, temporary export) sound?
