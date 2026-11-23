# Runtime capabilities

Status: design note, 2026-11-23. Companion to `docs/procedures/RUNTIME-ADAPTERS.md`.

Goal: know, per agent runtime, which parts of this workspace work natively and where the
adapter has to fill a gap. Every cell carries a source tag (see "Sources" at the end).
`mem` means from memory, not checked against a document on 2026-11-23. `n/d` means the
fetched official page does not document it.

## Owner test, 2026-11-22

Observed by the owner on 2026-11-22, running this workspace on each runtime:

- The base works on every runtime tested.
- rex works partially.
- Subagents were broken on about half of the runtimes.

Which runtimes had broken subagents, and which rex parts failed, is not recorded in this
note. Put machine results in the local inventory DB (AGENTS.md) and add a per-runtime
"observed" column to the overview once they are written down.

## Overview

| Runtime | Rules file | Skills / commands | Native subagents | Pre-tool hook can block | MCP client | One-shot mode |
|---|---|---|---|---|---|---|
| Claude Code | `CLAUDE.md` (here: `@AGENTS.md`) [S4] | skills `.claude/skills/<n>/SKILL.md` [mem; S4 layout] | yes, `.claude/agents/*.md`, nest up to 3 [C3] | yes, `PreToolUse` exit 2 or `deny`; fires in subagents [C1] | yes, `.mcp.json`, `--mcp-config` [C2] | `claude -p "..."` [C2] |
| rex | `AGENTS.md` (project file only with `workspace.trust: true`) [S3] | skills `.rex/skills/<n>/SKILL.md` (project skills need trust) [S3] | no, by design ("the orchestrator above rex does that") [S3] | yes, `hooks.pre_tool` command, user config only [S3] | yes, stdio [S3] | `python3 -m runtime "..."` [S3] |
| opencode | `AGENTS.md`, falls back to `CLAUDE.md` [O6] | commands `.opencode/commands/*.md` [O4]; skills `.opencode/skills`, `.claude/skills`, `.agents/skills` [O5] | yes, `.opencode/agents/*.md`, `subagent` tool [O1] | partly: plugin `execute.before` can change input; permission `evaluate` hook can return deny [O2] | yes, local + remote [O8] | `opencode run "..."` [O3] |
| goose | `AGENTS.md`, `.goosehints` [G6] | recipes as slash commands [G4]; skills `.claude/skills`, `.goose/skills`, `.agents/skills` [G5] | yes, internal; only in autonomous mode; no nesting [G1] | n/d (no hook found) [G1, G6] | yes, extensions are MCP servers [mem] | `goose run --no-session -q -t "..."` [G3] |
| codex CLI | `AGENTS.md` [mem] | skills `.agents/skills` [X4] | yes, `.codex/agents/*.toml` [X2] | yes, `PreToolUse` exit 2 or `deny`; project hooks need trust [X1] | yes [mem; X2 mentions MCP] | `codex exec "..."` [X3] |
| aider | none automatic; `--read AGENTS.md` or `read:` in `.aider.conf.yml` [A1] | none [mem] | none [mem] | none [mem] | none [mem] | `aider --message "..." <files>` [A2] |
| gemini CLI | `GEMINI.md` (here: points to `AGENTS.md`); `context.fileName` can list more [M6] | commands `.gemini/commands/*.toml` [M4]; skills `.gemini/skills`, `.agents/skills` [M5] | yes, `.gemini/agents/*.md`, on by default, no nesting [M2] | yes, `BeforeTool` exit 2 or `deny` [M1] | yes [mem] | `gemini -p "..."` [M3] |

## Permissions and model endpoint

| Runtime | Permission / approval model | Custom endpoint (for kiko) |
|---|---|---|
| Claude Code | allow/ask/deny rules, modes (`dontAsk`, `acceptEdits`, `auto`); in `-p` an unanswered ask is denied [C2] | Anthropic format only, `ANTHROPIC_BASE_URL` [C4]. kiko serves this (`/v1/messages`, `127.0.0.1:4000`), tested 2026-11-22 [S1, S2] |
| rex | deny > ask > allow > mode default; bash allow is a strict whitelist; one-shot with `--json` or redirected stdio denies every ask [S3] | OpenAI-compatible, `RUNTIME_LITELLM__BASE_URL` [S3] |
| opencode | ordered allow/ask/deny rules per action + pattern, last match wins, default ask; `run` handling of ask n/d [O9] | OpenAI-compatible provider, `settings.baseURL` [O7] |
| goose | modes: autonomous, manual approval, smart approval, chat only [G2] | `OPENAI_HOST` / `OPENAI_BASE_PATH` [G6] |
| codex CLI | sandbox (`read-only` default in exec, `workspace-write`, `danger-full-access`) + approval policy [X3] | `model_providers.<id>.base_url`, `wire_api = "responses"` (user config only) [X5] |
| aider | confirm prompts; `--yes` answers all of them [A2] | `OPENAI_API_BASE` + model `openai/<name>` [A3] |
| gemini CLI | `default`, `auto_edit`, `plan`; `yolo` only from the command line [M6] | Gemini API format only, `GOOGLE_GEMINI_BASE_URL` [M6]; OpenAI-compatible n/d |

kiko note: the owner's kiko repository documents an Anthropic `/v1/messages` gateway on
`127.0.0.1:4000` and does not state an OpenAI `/v1/chat/completions` endpoint [S1]. rex's
README uses an OpenAI-compatible "kiko-lite" endpoint on `127.0.0.1:5000` [S3]. So Claude
Code talks to kiko; opencode, goose, aider and rex need the OpenAI-compatible endpoint;
codex needs the Responses API; gemini CLI needs the Gemini API format.

## Subagent fallback: launch command per runtime

The fallback runs one role as a separate one-shot process of the same runtime, in the
project folder, and reads its final answer from stdout. Tags as above.

| Runtime | Fallback command (brief on the command line or stdin) | Notes |
|---|---|---|
| Claude Code | `claude -p "<brief>" --output-format json --permission-mode dontAsk --allowedTools "<list>"` [C2] | needed only if native subagents fail on the machine; they are documented and hooks fire inside them [C1, C3] |
| rex | `python3 -m runtime --json "<brief>"` [S3] | the only way: no subagents by design; asks are denied, so the role's allow rules must be set |
| opencode | `opencode run -m <provider/model> "<brief>"` [O3, S4]; `--agent <role>` [mem] | ask handling in `run` n/d: test before relying |
| goose | `goose run --no-session -q -t "<brief>"`, role as `--recipe <file>` [G3] | native subagents only in autonomous mode [G1] |
| codex CLI | `codex exec --json --sandbox workspace-write "<brief>"` [X3] | |
| aider | `aider --message "<brief>" --read AGENTS.md --no-auto-commits <files>` [A1, A2] | edits only the listed files; no guard (see gaps) |
| gemini CLI | `gemini -p "<brief>" --output-format json` [M3] | approval handling in headless mode n/d |

## Gaps and the adapter fix

1. **Subagents.** Native subagents exist in Claude Code, opencode, goose, codex and
   gemini CLI, but with different rules: goose only in autonomous mode, gemini and goose
   without nesting, rex none by design, aider none. The owner saw subagents fail on about
   half of the runtimes (2026-11-22). Fix: the adapter declares a `subagents` capability
   only where a smoke test proves it; elsewhere `spawn_role()` falls back to the one-shot
   process above. When even that is not wanted, `docs/procedures/orchestration.md` "No
   subagents" (one agent plays the roles in turn) stays the last fallback.
2. **The fallback conflicts with two current rules.** AGENTS.md says never start
   claude, gemini, goose, codex or another opencode process unless the user names it in an
   order, and RUNTIME-ADAPTERS.md Rule 4 says one runtime process per session. The
   fallback needs both rules amended: the adapter (not the model) may start one child of
   the same runtime per role, only when the user ordered orchestrated work, and the child
   gets the same rules file and the same deny list. Until that is decided and written,
   the fallback is design only.
3. **Guards are not equal.** A blocking pre-tool hook is documented for Claude Code,
   codex, gemini CLI and rex. opencode has a permission `evaluate` hook that can deny, but
   whether `execute.before` can block is not documented. goose has no documented hook;
   aider has none. On those runtimes the push guard (`confirm_push()`) and the secret
   rules are instructions plus permission settings, not enforcement. Say so in each
   adapter's capability set; do not claim a guard that is not there.
4. **Hooks in a child process.** A separate process loads its own config: Claude `-p`
   runs the project hooks without a trust dialog [C2]; codex runs project hooks only after
   they are trusted [X1]; rex reads hooks and permissions only from the user config [S3].
   The adapter must check, per runtime, that the guard is active in the child before it
   starts one.
5. **Skills reach.** `.claude/skills` is read by Claude Code, opencode and goose;
   `.opencode/commands` only by opencode. codex reads only `.agents/skills`, gemini CLI
   `.gemini/skills` or `.agents/skills`, rex `.rex/skills`. A shared `.agents/skills`
   folder (same thin pointers to `docs/procedures/`) would cover codex, gemini CLI,
   opencode and goose; rex needs its own folder or a `skills.paths` entry, plus trust.
6. **Rules reach.** rex reads the project `AGENTS.md` only with `workspace.trust: true`;
   aider reads nothing by itself and needs `--read AGENTS.md`. Without these the agent runs
   without the workspace rules. Whether this explains "rex partially" on 2026-11-22 is not
   verified.
7. **Endpoint formats.** One kiko endpoint does not serve all runtimes: Anthropic format
   (Claude Code), OpenAI chat format (rex, opencode, goose, aider), Responses API (codex),
   Gemini format (gemini CLI). The adapter records which format each runtime needs.

## Not verified

- `mem` cells, the opencode `--agent` flag, and approval handling in `opencode run` and
  `gemini -p`.
- goose pages were read from the `goose-docs.pages.dev` mirror of the goose docs; the
  context-file and endpoint facts [G6] come from search-result summaries of goose-docs.ai,
  whose pages did not render for the fetcher.
- No row was re-tested for this note; only the owner's 2026-11-22 run is observed data.

## Sources

All web pages were read on 2026-11-23 unless a date says otherwise.

- [S1] kiko / ai_runtime repository README, https://github.com/peterkokosharov/ai_runtime
  (branch `master`), read 2026-11-23. It holds no per-runtime table; Claude Code is the
  only agent runtime it describes.
- [S2] ai_runtime `KIKO.md`, https://github.com/peterkokosharov/ai_runtime/blob/master/KIKO.md,
  Claude Code run against kiko verified 2026-11-22; read 2026-11-23.
- [S3] rex repository (local): `README.md` and `docs/plans/2026-11-23-rex-gaps.md`, commit
  `4a57eec` of 2026-11-23.
- [S4] this repository: `AGENTS.md`, `CLAUDE.md`, `GEMINI.md`, `README.md`,
  `docs/procedures/RUNTIME-ADAPTERS.md`, `docs/procedures/orchestration.md`,
  `.claude/skills/`, `.opencode/commands/`, commit `23fd896` of 2026-11-23.
- [C1] https://code.claude.com/docs/en/hooks
- [C2] https://code.claude.com/docs/en/headless
- [C3] https://code.claude.com/docs/en/sub-agents
- [C4] https://code.claude.com/docs/en/llm-gateway
- [O1] https://opencode.ai/docs/agents/
- [O2] https://opencode.ai/docs/build/plugins/server
- [O3] https://opencode.ai/docs/cli/
- [O4] https://opencode.ai/docs/commands/
- [O5] https://opencode.ai/docs/skills/
- [O6] https://opencode.ai/docs/rules/
- [O7] https://opencode.ai/docs/providers/
- [O8] https://opencode.ai/docs/mcp-servers/
- [O9] https://opencode.ai/docs/permissions/
- [G1] https://goose-docs.pages.dev/docs/guides/subagents
- [G2] https://goose-docs.pages.dev/docs/guides/goose-permissions
- [G3] goose-run(1) man page, https://www.mankier.com/1/goose-run
- [G4] https://goose-docs.pages.dev/docs/guides/context-engineering/slash-commands
- [G5] https://goose-docs.pages.dev/docs/guides/context-engineering/using-skills
- [G6] search-result summaries of https://goose-docs.ai/docs/guides/context-engineering/using-goosehints
  and https://goose-docs.ai/docs/guides/environment-variables (pages not rendered)
- [X1] https://learn.chatgpt.com/docs/hooks (redirect from developers.openai.com/codex/hooks)
- [X2] https://learn.chatgpt.com/docs/agent-configuration/subagents
- [X3] https://learn.chatgpt.com/docs/non-interactive-mode
- [X4] https://learn.chatgpt.com/docs/build-skills
- [X5] https://learn.chatgpt.com/docs/enterprise/connect-to-a-gateway
- [A1] https://aider.chat/docs/usage/conventions.html
- [A2] https://aider.chat/docs/scripting.html
- [A3] https://aider.chat/docs/llms/openai-compat.html
- [M1] https://geminicli.com/docs/hooks/
- [M2] https://geminicli.com/docs/core/subagents/
- [M3] https://geminicli.com/docs/cli/headless/
- [M4] https://geminicli.com/docs/cli/custom-commands/
- [M5] https://geminicli.com/docs/cli/skills/
- [M6] https://geminicli.com/docs/reference/configuration/
- Owner test run of this workspace on all runtimes: observed by the owner, 2026-11-22.
