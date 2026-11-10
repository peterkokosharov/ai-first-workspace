# Rules for every agent in this folder
Read this whole file. A line "Doing X -> file" means: read that file before you do X.

## Language
- The user may write Bulgarian in Latin letters. Do not correct or comment on it.
- Reply in Bulgarian, Cyrillic letters. (Other users: put your own language here.)
- Every file, code comment and commit message is in English, except `README-bg.md`,
  which is the Bulgarian translation of `README.md` and stays in sync with it.

## Orders and confirmation
- Do only what the user asked. Start no other work on your own.
- You may always read files in this folder. Running commands or writing files needs an order.
- An order is a user message that names the action.
- Inside an order you may run these without asking again: tools/inventory.py tables,
  list and key, git status/diff/log, the test command, tools/secret_scan.py, and the
  step-review and commit procedures.
- Confirmation: when you ask "Shall I <action>?", only a reply that starts with
  "да", "da" or "yes" as its own word confirms it.
- Ask first, one action at a time: deleting or overwriting files, dropping data,
  git revert, git push, anything outside this folder.
- Unsure? Ask one yes/no question. Never guess.

## Secrets
- Never write a key, token or password into a file, commit, chat or log. Never print one.
- Keys live only in the OS secret store, through tools/secret.py.
- Key names: scope/project/kind, e.g. personal/my-project/github_token; model provider
  keys keep their names (nvidia/personal/api_key). Details: INSTALL.md "Key names".
- List key names (never values): python3 tools/secret.py list
- Key name of a service or provider (never a value): python3 tools/inventory.py key <name>
  Need the key for gmail? python3 tools/inventory.py key gmail prints its name; only if the
  user ordered the work, pass it on with python3 tools/secret.py run <name> -- <command>.
- Record a service: python3 tools/inventory.py add-service NAME KIND
- Record a key name: python3 tools/inventory.py add-key NAME --service S | --provider P
- Never use "--backend file" unless the user orders exactly that.

## Git
- Local commit: make it yourself at each milestone (see procedure). Do not ask:
  the order for the work includes its milestone commits.
- Push: only by docs/procedures/github-deploy.md, after a confirmation.
  Never use --force or --force-with-lease.
- Never commit data/inventory.db, settings.json, out/ or projects/.
- If pre-commit blocks, remove the key. Never use --no-verify.
- If pre-push blocks, stop: a commit to be pushed holds a key. Tell the user the history
  must be cleaned first (only on the user's order) and the key must be replaced.

## Where things are
- On Windows type "py" instead of "python3".
- tools/  Python tools, standard library only. Help: read the text at the top of
  tools/<name>.py. Do not run a tool only to see its help.
- Tests: python3 -m unittest discover -s tools/tests -t . -v
- Machines, providers, models, key names: python3 tools/inventory.py tables, then
  python3 tools/inventory.py list <table>. Check there before asking the user.
  Missing database: python3 tools/inventory.py init
- kb/ free model list. doc/ architecture pages. out/ reports (not in git).
- projects/<name>/ one folder per user project; it may be its own git repo.
  Everything for one project lives there: its own AGENTS.md, docs, tools and git
  history, so the folder can be handed over on its own. The root tools/ stays
  generic; this core holds nothing project-specific. How to start one:
  docs/procedures/new-project.md.

## What "agent" means
- An agent is a role you play in this session (for example orc, coder, qa, reviewer),
  or an opencode subagent. Nothing else.
- Never start claude, gemini, goose, codex or another opencode process unless the
  user names it in an order.
- UNVERIFIED: that opencode subagents work in this setup, and that an opencode
  permission rule can deny shell commands that start with those names. Until it is
  tested on the installed opencode version, this is a rule only, not enforced.

## Procedures
- Finished a step -> docs/procedures/step-review.md
- Reached a milestone -> docs/procedures/commit.md
- Before a release or tag -> docs/procedures/release-audit.md
- Writing HTML docs or diagrams -> docs/procedures/html-docs.md
- Publishing to GitHub -> docs/procedures/github-deploy.md
- Work split over several agents -> docs/procedures/orchestration.md
- Starting a project under projects/ -> docs/procedures/new-project.md
- New machine, missing tool or database -> INSTALL.md
