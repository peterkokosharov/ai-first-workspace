# Rules for every agent in this folder

Read this whole file first. A line "Doing X -> file" means: read that file before you do X.

## Language
- The user may write Bulgarian in Latin letters. Do not correct or comment on it.
- Reply in Bulgarian, Cyrillic letters. (Other users: put your own language here.)
- Every file, code comment and commit message is in English, except `README-bg.md`,
  which is the Bulgarian translation of `README.md` and stays in sync with it.

## Orders and confirmation
- Do only what the user asked. Start no other work on your own.
- You may always read files in this folder. Running commands or writing files needs an order.
- An order is a user message that names the action.
- Inside an order you may run these without asking again: `tools/inventory.py` tables,
  list and key, `git status/diff/log`, the test command, `tools/secret_scan.py`, and the
  step-review and commit procedures.
- Ask first, one action at a time: deleting or overwriting files, dropping data,
  git revert, rewriting history (`rebase`, `amend` on a pushed commit, `filter-branch`),
  git push, anything outside this folder.
- Confirmation: when you ask "Shall I <action>?", only a reply that starts with
  "да", "da" or "yes" as its own word confirms it.
- Unsure? Ask one yes/no question. Never guess.

## Commands
- On Windows type `py`, not `python3`.
- On Windows the shell may be PowerShell, which parses a `|` inside a quoted pattern
  (grep, findstr) and breaks the command. Check which shell you have; use the grep tool,
  or run bash explicitly (`bash -c '<one line>'` from Git for Windows).
- Core tests (a minute or two): `py -m unittest discover -s tools/tests -t . -v`
- One core test: `py -m unittest tools.tests.test_bundle -v`
- A project's tests: the same discover command, run from `projects/<name>/`.
- Run the suites one at a time. Two runs at once make `test_secret` fail and skip tests:
  it uses the machine's one OS secret store. A failure there is the environment, not the code.
- Secret check: `py tools/secret_scan.py` scans staged files. The commit hooks run it
  only after `tools/bootstrap.sh` has set `core.hooksPath`. Check:
  `git config core.hooksPath` (expected `.githooks`). If it is empty, run the scan
  yourself after `git add`; without it nothing checks the commit.
- Handover bundle: `py tools/bundle.py <name>` (slow: it runs the project's tests). It writes
  `out/bundles/<name>/` with the core and the project, clears `CORE`, proves the bundled
  project reaches the bundled core, and runs the project's tests inside it. `--force` rebuilds.

## Secrets
- Never write a key, token or password into a file, commit, chat or log. Never print one.
  Do not run `env`, `set` or `printenv` when opencode's keys may be in the environment.
- Keys live only in the OS secret store, through `tools/secret.py`.
- Key names: scope/project/kind, e.g. personal/my-project/github_token; model provider
  keys keep their names (nvidia/personal/api_key). Details: INSTALL.md "Key names".
- List key names (never values): `py tools/secret.py list`
- Key name of a service or provider: `py tools/inventory.py key <name>`. Only if the user
  ordered the work, pass it on with `py tools/secret.py run <name> -- <command>`.
- Record a service: `add-service NAME KIND`; a key name: `add-key NAME --service S | --provider P`.
- Never use `--backend file` unless the user orders exactly that.

## Git
- Local commit: make it yourself at each milestone (docs/procedures/commit.md); the order
  for the work includes its commits. Add files by name, never `git add .` or `git add -A`.
- Push: only by docs/procedures/github-deploy.md, after a confirmation.
  Never use `--force` or `--force-with-lease`.
- Never commit `data/inventory.db`, `settings.json`, `out/` or `projects/`.
- If the secret scan blocks, remove the key. Never use `--no-verify`.
- If a pre-push check blocks, stop: the history to be pushed holds a key. Say so and wait
  for an order to clean it; the key itself must be replaced too.
- This repository is public and generic. Never put a project or client name in it -- not
  in `data/seed.sql`, tests, docs or examples. Seed rows are `example-project`,
  `second-project`, `third-project`. A name in a pushed commit cannot be removed without
  rewriting history.
- `git` on Windows rewrites LF to CRLF (`core.autocrlf=true`). A test that compares two
  copies of a file must compare lines, not bytes, or it fails only inside a bundle.

## Where things are
- `tools/` Python tools, standard library only. Help: read the text at the top of
  `tools/<name>.py`; do not run a tool only to see its help.
- Machines, providers, models, key names: `py tools/inventory.py tables`, then
  `list <table>`. Check there before asking the user. Missing database: `inventory.py init`.
- The free model list ships in `data/models.xml`; a fresher one in the folder named by
  `paths.kb` in the local `settings.json` (a model lab, for example) takes its place.
  `docs/design/` architecture pages. `out/` reports and audits (not in git).
- `projects/<name>/` one folder per user project, its own git repository and its own
  `AGENTS.md`. It runs on this core: `tools/core.py`, `tools/secret.py` and
  `tools/__init__.py` are the glue (template: `templates/project/tools/`); a project
  imports core tools through it and never holds a copy of one. Read the project's rules before
  touching it; this file does not govern it. New project: docs/procedures/new-project.md.
- Only free-tier models. No paid provider and no paid key without an explicit order.

## What "agent" means
- An agent is a role you play in this session (for example orc, coder, qa, reviewer), or
  an opencode subagent. Nothing else.
- Never start claude, gemini, goose, codex or another opencode process unless the user
  names it in an order.
- Whether subagents work, and whether an opencode permission rule can deny shell commands
  starting with those names, depends on the installed opencode. Treat the rule as a
  request, not a guarantee; machine-specific results belong in the local inventory DB.

## Procedures
- Finished a step -> docs/procedures/step-review.md
- Reached a milestone -> docs/procedures/commit.md
- Before a release or tag -> docs/procedures/release-audit.md
- Writing HTML docs or diagrams -> docs/procedures/html-docs.md
- Publishing to GitHub -> docs/procedures/github-deploy.md
- Work split over several agents -> docs/procedures/orchestration.md
- Starting a project under projects/ -> docs/procedures/new-project.md
- New machine, missing tool or database -> INSTALL.md
