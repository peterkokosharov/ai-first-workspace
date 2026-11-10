# Start a project under projects/

Goal: add a project as its own folder with its own git repository, so that it can be
copied, handed over or sold together with the core, and so that one client's work never
enters the core's history.

## Why a project has its own repository

- The core is generic: tools, rules, a model list. A project is one client's business:
  offers, contracts, reports, and the code written for them. Mixed together, the core's
  history carries client names and the project cannot be handed over.
- A project may be sold, given to a colleague, or pushed to a different remote with
  different access (a client's own GitHub organisation). Its history must travel with it.
- `projects/` is gitignored in the core (`.gitignore`, line `/projects`), so the core never
  tracks a project. Every project folder is its own repository, root at that folder, and
  its history belongs to the project alone.
- The dependency runs one way only: the core never needs a project, and a project does
  need the core at runtime. Handing a project over means handing over the core with it;
  `tools/bundle.py` does exactly that in one folder.
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
   - the three glue files that reach the core: `tools/core.py`, `tools/secret.py` and a
     `tools/__init__.py` that calls `core.install()`. Copy them from the core's template,
     `templates/project/tools/` (`cp templates/project/tools/*.py projects/<name>/tools/`
     from the core root, after creating `tools/`); they are the same in every project and
     hold no project code;
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

## The core is the runtime

A project runs on the core. `tools/core.py` in the project finds it, and
`tools/__init__.py` registers the core's secret store as the module `secret`, which
`google_api.py` imports. Search order: `<project>/vendor/` first, then the `CORE`
environment variable, then the project's `settings.json` (`"core"`), then upwards to the
first folder that holds both `AGENTS.md` and `tools/secret.py`. The `vendor/` copy is
optional, and `tools/bundle.py` does not make one: a bundle carries the whole core
instead.

Three rules follow:

- Do not copy a core tool into a project so that it starts. If a project needs one more
  shared tool, put that tool in the core and let the project reach it. The only exception
  is the three glue files above: they are the border, not a copy of a tool.
- Do copy the whole runtime at handover: `py tools/bundle.py <name>` in the core builds
  one folder with the core and the project, and runs the project's tests inside it.
- If a project holds a copy of a core tool (`google_api.py` is one), the core's copy is
  the original. Change the core first, copy the file over, and let the project's test
  fail when the two differ (line endings aside: git rewrites them on checkout).

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
- Handing over or selling: build a bundle from the core, `py tools/bundle.py <name>`
  (writes `out/bundles/<name>/`; `--force` replaces it). The bundle holds the core and
  the project, and never `data/inventory.db`, `settings.json` or the core's own git
  history. Check before it leaves:
  - the script printed `tests:` and then `OK`;
  - the project inside the bundle reaches the bundle's own core (`tools/bundle.py`
    refuses to build one that reaches another);
  - `git log` in the bundle's project shows its history and `git status` is clean;
  - `LICENSE` (MIT) is at the top of the bundle;
  - no secret inside.

## Checklist

- [ ] `projects/<name>/AGENTS.md` exists and names the boundary.
- [ ] `git init -b main` done inside the folder, first commit made.
- [ ] `.gitignore` covers `.tmp/`, `__pycache__/` and what the project writes.
- [ ] The project's tests pass inside the bundle (`tools/bundle.py` prints `tests:` and `OK`).
- [ ] A row for it exists in the local database (`add-project`).
- [ ] No secret, no excluded client material, no local file (`inventory.db`,
      `settings.json`) in the bundle.
