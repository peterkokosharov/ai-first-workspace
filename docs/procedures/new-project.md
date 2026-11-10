# Start a project under projects/

Goal: add a project as its own folder with its own git repository, so that it can be
copied, handed over or sold on its own, and so that one client's work never enters the
core's history.

## Why a project has its own repository

- The core is generic: tools, rules, a model list. A project is one client's business:
  offers, contracts, reports, and the code written for them. Mixed together, the core's
  history carries client names and the project cannot be handed over.
- A project may be sold, given to a colleague, or pushed to a different remote with
  different access (a client's own GitHub organisation). Its history must travel with it.
- `projects/` is gitignored in the core (`.gitignore`, line `/projects`), so the core never
  tracks a project. Every project folder is its own repository, root at that folder, and
  its history belongs to the project alone.
- The dependency runs one way only. The project must work when the core is absent; the
  core must work when the project is absent. When both are present the core is a helper,
  never a dependency.
- One step, one commit, inside the project's own repository. The core's commits never
  describe project work.

## Steps

1. Create the folder and its repository.
   ```bash
   mkdir -p projects/<name>
   cd projects/<name>
   git init -b main
   ```
2. Write `projects/<name>/AGENTS.md` before anything else. It is the project's whole rule
   set and the first file every agent reads. Start from the core's `AGENTS.md` and keep
   only what that project needs: what the project is, the boundary (own `doc/`, own
   `tools/`, own history), language, orders and confirmation, secrets, git, working style.
3. Create what the project needs and nothing more:
   - `doc/` — plans, setup pages, decisions;
   - `tools/` — only the tools this project uses, standard library only, plus `tools/tests/`;
   - `.gitignore` — at least `.tmp/`, `__pycache__/`, `*.pyc`, `*.pyo`, plus whatever the
     project writes.
4. Run the project's own tests from its own folder:
   ```bash
   py -m unittest discover -s tools/tests -t . -v      # python3 on Linux
   ```
   A new project has no tests yet. Add the first test with the first tool, not later: a
   tool without a test is a guess.
5. Record the project in the local database, from the core root:
   ```bash
   py tools/inventory.py add-project <name> --title "<human name>" --kind <kind>
   ```
   This writes only `data/inventory.db` (gitignored). It commits nothing.
6. Commit inside the project, by file name, following `docs/procedures/commit.md`.

## Copying a core tool into a project

If a project needs one of the core's tools, copy the file into the project's `tools/`,
give it tests there, and write one line in the project's `doc/` saying where the copy came
from and that the core's copy is the original. Keep the two identical while they are
identical; when the project changes its copy, record why. Never import from the parent:
`import` across the boundary breaks the handover.

## Never

- Never `git add` a project path in the core. `/projects` is gitignored; if a project path
  ever appears in the core's `git status`, stop and fix `.gitignore` before committing.
- Never put a key, token or client secret in the project. Keys live in the OS secret store
  through `tools/secret.py`; a project holds no secrets, not even a sample one.
- Never let the core's rules govern a project. Every agent reads the project's own
  `AGENTS.md` first.
- Never push a project as part of the core. Different repository, different remote,
  separate confirmation.

## Push and handover

- Push a project to its own remote by `docs/procedures/github-deploy.md`, after the
  owner's confirmation. Pushing the core never publishes a project.
- Handing over or selling: copy the folder. It must contain its rules, its documents, its
  tools, its tests and its history. Check before it leaves:
  - `git log` shows the history and `git status` is clean;
  - `py -m unittest discover -s tools/tests -t .` passes in the copied folder alone;
  - no path points outside the folder, no `import` of a parent package, no secret inside.

## Checklist

- [ ] `projects/<name>/AGENTS.md` exists and names the boundary.
- [ ] `git init -b main` done inside the folder, first commit made.
- [ ] `.gitignore` covers `.tmp/`, `__pycache__/` and what the project writes.
- [ ] The project's tests pass from its own folder, with no parent present.
- [ ] A row for it exists in the local database (`add-project`).
- [ ] No secret, no excluded client material, no import from the core.
