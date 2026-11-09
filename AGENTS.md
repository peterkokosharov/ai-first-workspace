# Rules for every agent in this folder
Read this whole file. A line "Doing X -> file" means: read that file before you do X.

## Language
- The user may write Bulgarian in Latin letters. Do not correct or comment on it.
- Reply in Bulgarian, Cyrillic letters. (Other users: put your own language here.)
- Every file, code comment and commit message is in English.

## Orders and confirmation
- Do only what the user asked. Start no other work on your own.
- You may always read files in this folder. Running commands or writing files needs an order.
- An order is a user message that names the action. When you ask "Shall I <action>?",
  only a reply that starts with "да" or "yes" as its own word confirms it.
- Ask first, one action at a time: deleting or overwriting files, dropping data,
  git revert, anything outside this folder. Never git push (a human pushes).
- Unsure? Ask one yes/no question. Never guess.

## Secrets
- Never write a key, token or password into a file, commit, chat or log. Never print one.
- Keys live only in the OS secret store, through tools/secret.py.
  Names look like provider/scope/kind, e.g. nvidia/personal/api_key.
- List key names (never values): python3 tools/secret.py list
- Never use "--backend file" unless the user orders exactly that.

## Git
- Commit at each milestone (see procedure). Never push.
- Never commit data/inventory.db, settings.json, out/ or projects/.
- If the pre-commit hook blocks a commit, remove the key. Never use --no-verify.

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

## Procedures
- Finished a step -> docs/procedures/step-review.md
- Reached a milestone -> docs/procedures/commit.md
- Before a release or tag -> docs/procedures/release-audit.md
- Writing HTML docs or diagrams -> docs/procedures/html-docs.md
- Publishing to GitHub -> docs/procedures/github-deploy.md
- Work split over several agents -> docs/procedures/orchestration.md
- New machine, missing tool or database -> INSTALL.md
