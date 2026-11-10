# Install — AI-first workspace

**The easiest install:** clone this folder, run `autodiscovery.py`, add your API key, and start coding with any agent harness.

Made for a cheap laptop (4-8 GB RAM) with Windows 10/11 or Linux Mint; no local models.
Tested on **Windows 10** and **Q4OS Linux (TDE)**; Linux Mint is the next test platform.
On Windows use `py` where this page says `python3`.

---

## What the machine needs

4-8 GB RAM is enough: the models run in the cloud on free tiers, nothing runs locally.

**Linux Mint / Ubuntu:**

```bash
sudo apt install python3 git gnome-keyring libsecret-tools   # nodejs npm: optional, diagrams only
```

For pushing to GitHub, git's own keyring helper comes as source and is built once
(from memory, check on your machine):

```bash
sudo apt install libsecret-1-dev build-essential
sudo make -C /usr/share/doc/git/contrib/credential/libsecret
```

**Windows 10/11:** install **Git for Windows** (https://git-scm.com/; it brings Git Bash
and Git Credential Manager, which keeps tokens in Windows Credential Manager) and
**Python 3.10 or newer** from python.org (run it as `py`). node.js is optional (diagrams only).

Then run `python3 tools/autodiscovery.py` (`py` on Windows): it shows what is missing.
With `--save` it also writes the found program paths into `settings.json` and this
machine into the inventory database.

---

## 1. Clone / unpack the project

```bash
# Option A: clone from GitHub
git clone https://github.com/peterkokosharov/ai-first-workspace.git
cd ai-first-workspace

# Option B: unpack an archive of the folder and cd into it
```

---

## 2. Install an agent

Install at least one, following its own install page (no admin rights needed for the
user installs). **opencode** is the default: it has free models and costs nothing.

- **opencode** — reads `AGENTS.md` (installer from https://opencode.ai, or
  `npm install -g opencode-ai`).
- **Gemini CLI** — reads `GEMINI.md`, which points to `AGENTS.md` (free plan, limits).
- **Claude Code** — reads `CLAUDE.md`, which points to `AGENTS.md` (needs a paid plan).
- **goose** — reads `AGENTS.md`; download it from its releases page and put it on `PATH`.
- Codex CLI reads `AGENTS.md` but is not tested with this workspace.

On Windows install **Git for Windows** (https://git-scm.com/) first; it brings Git Bash.

---

## 3. Install the workspace

```bash
# Check the environment (python3, git, bash, inventory db). The secret-store check
# is read-only; --probe-write also writes/reads/deletes a random probe entry,
# --no-secret-probe skips it.
python3 tools/autodiscovery.py

# Create the SQLite inventory database
python3 tools/inventory.py init

# Verify everything works (tests never touch your real secret store unless
# SECRET_LIVE_TESTS=1 is set)
python3 -m unittest discover -s tools/tests -t . -v
```

On Windows (Git Bash) the same with the `py` launcher:

```bash
py tools/autodiscovery.py
py tools/inventory.py init
py -m unittest discover -s tools/tests -t . -v
```

Or run everything at once (Linux and Git Bash on Windows; it picks `python3`,
`python` or `py` itself and also turns on the secret check below):

```bash
bash tools/bootstrap.sh
```

### What auto-discovery checks

Run `tools/autodiscovery.py` first on a new machine, and again whenever
`tools/secret.py` or `data/inventory.db` is missing or does not work. It checks the
OS, processor, RAM, Python, git, bash, opencode, node, npm, mermaid-cli (settings key
`merman`), docker, docker-compose, the two tools `secret.py` and `inventory.py`, the
secret store and `data/inventory.db`. Program names come from `settings.json` (copy of
`settings.json.example`). The minimum is git, bash and Python; a GitHub token and
e-mail are optional.

| Exit code | Meaning | What to do next |
|-----------|---------|-----------------|
| 0 | OK, minimum met | Go on with the task |
| 2 | `data/inventory.db` missing (checked first: also returned when git, bash or Python is missing too) | `python3 tools/inventory.py init`, run it again |
| 3 | `data/inventory.db` has no tables (checked second, same rule) | `python3 tools/inventory.py init`, run it again |
| 1 | Database fine, but git, bash or Python missing, or a tool file missing | Install the missing piece, run it again |

The report printed above the exit code always lists every missing piece.

`tools/secret.py` exit codes: 0 OK, 1 key not found, 2 store error, 3 usage error.
Its default store choice (`auto`) never falls back to a plain-text file.

### Turn on the secret check (once per clone)

```bash
git config core.hooksPath .githooks
```

`tools/bootstrap.sh` does this for you when the folder is a git repo (running it again
changes nothing). From then on every `git commit` runs `tools/secret_scan.py`, which
refuses a commit that contains an API key or token (NVIDIA `nvapi-…`, `sk-…`, GitHub
`ghp_…` / `github_pat_…`, AWS `AKIA…`, Google/Gemini `AIza…`, or a literal
`api_key: <value>`). The value itself is never printed. Scan the whole tree by hand with
`python3 tools/secret_scan.py --all`.

The same setting turns on a second hook: every `git push` first runs
`tools/secret_scan.py --push`. It scans the lines added by every commit the push would
publish (for a new branch: every commit not yet on a remote) and refuses the push if one
adds a key, even when a later commit removed it again. A deleted branch passes.

**Note:** if no Python 3.10 or newer is found when you commit, the hook prints
`pre-commit: Python 3.10+ not found, secret scan skipped` and lets the commit through
(exit 0), so a machine without Python can still commit. The push hook does the same
(`pre-push: Python 3.10+ not found, secret scan skipped`). On such a machine the check
does not protect you; install Python or scan by hand before you push.

---

## 4. Add your AI provider key

The main provider is NVIDIA (free account at build.nvidia.com, about 20 free models;
the list ships in `data/models.xml`; `tools/gen_models_xml.py` can build a fresher one into
the folder `paths.kb` from `settings.json`, which then takes its place). Gemini and ChatGPT free plans are optional and have
tight limits.

```bash
# NVIDIA (free)
python3 tools/secret.py set nvidia/personal/api_key

# Gemini (optional, free plan with limits)
python3 tools/secret.py set gemini/personal/api_key
```

The key goes to the OS store that `secret.py` picks automatically: Windows Credential
Manager on Windows, KWallet or the TDE wallet on Q4OS, GNOME Keyring (`secret-tool`) on
Mint/Ubuntu.

The value is read from **prompt/stdin** — never printed.

### Key names

- Form: `scope/project/kind`, scope = `personal` or `company`, e.g.
  `personal/my-book/github_token`, `company/acme/github_token`.
- Lowercase, at least two parts, no leading `/` (`secret.py` refuses other names).
- One key per project: with several projects open you see which key belongs where.
- Model provider keys keep their names (`nvidia/personal/api_key` and the others above).
- `git.token_key` in `settings.json` names the key this repo uses. A GitHub token is
  kept by git's credential helper, not by `secret.py` (docs/procedures/github-deploy.md).
- Record a name (never a value): `python3 tools/inventory.py add-key <name> --service github`.

---

## 5. Start your agent in this folder

```bash
opencode    # default, free models
gemini      # Gemini CLI
goose session
claude      # Claude Code (paid plan)
```

To connect opencode to the free NVIDIA models, run `tools/setup_nvidia.py` (add
`--dry-run` first to see the change). It writes the models into opencode's user config
but **never the key**: the config only names the variable `NVIDIA_API_KEY`. Then start
opencode with the launcher instead of plain `opencode`; it reads your keys from the OS
secret store and passes them to the opencode process only (not to your shell, not to a
file). Arguments go on to opencode.

```bash
python3 tools/setup_nvidia.py
python3 tools/run_opencode.py      # Windows (Git Bash): py tools/run_opencode.py
```

If an old config, one of its `.bak-*` copies or `./opencode.json` in the current folder
still holds a key in plain text, the tools warn and show where (never the value). The
setup tools remove entries older versions wrote and literal keys of the providers they
manage only once that key is in the OS secret store; otherwise they keep it and print
`python3 tools/secret.py set <path>` to run first. Keys of other providers are only
reported (`--redact-foreign` replaces them with a placeholder). Delete old `.bak-*` files
by hand once the keys are stored.

The keys are in opencode's environment: programs opencode starts can read them. An agent
must never print environment variables (`env`, `set`, `printenv`, `echo $..._API_KEY`).

If a free model thinks for too long or repeats itself: press Stop (Esc), type `/init`,
then continue.

---

## Working on outside repos

Your own repos can live outside the workspace and still be reached from it: make
`projects` a link to them (git ignores the root `projects`, folder or link).
First move or remove an existing `projects/` folder, otherwise the link cannot be made.

```bash
# Linux / macOS
ln -s ~/repos projects
# Windows (cmd; a junction needs no admin rights)
mklink /J projects %USERPROFILE%\repos
```

A project reached through the link finds the core by walking up the path as you typed
it (links are not resolved). A junction launch from cmd, Explorer or an absolute path
works by itself. In Git Bash, as on Linux and macOS, the current folder is physical, so
set `"core"` in `settings.json` or set `CORE`. Order: `vendor/`, `CORE`, `settings.json`,
upward walk on the given path, upward walk on the resolved path
(`docs/procedures/new-project.md`). The link's own location wins (a workspace above it is
trusted as the core), and `CORE` must be an absolute path.

Started from the real path (for example `C:\repos\X`) or from a physical current folder
(Git Bash, Linux, macOS) the walk cannot see the link: set `"core": "<path to the workspace>"` in the project's
`settings.json` or set `CORE`. `tools/link.py` will write that key for you; until then
set it by hand.

The workspace rules (`AGENTS.md`) are the base; a project's own `AGENTS.md` only adds to
them. `secret_scan.py --all` and the tests do not follow the link.

Each outside repo needs its own secret check. The workspace hooks find their scanner
next to themselves, so one setting is enough:

```bash
git -C <repo> config core.hooksPath <absolute path to this workspace>/.githooks
```

Do this only if the repo has no hooks of its own (an existing `core.hooksPath` is
yours: call the two hook scripts from your own hooks instead).

---

## Quick start (one-liner summary)

```bash
git clone https://github.com/peterkokosharov/ai-first-workspace.git
cd ai-first-workspace
python3 tools/autodiscovery.py
python3 tools/inventory.py init
git config core.hooksPath .githooks
python3 tools/secret.py set nvidia/personal/api_key
python3 -m unittest discover -s tools/tests -t . -v
```

Windows (Git Bash), same steps with `py`:

```bash
git clone https://github.com/peterkokosharov/ai-first-workspace.git
cd ai-first-workspace
py tools/autodiscovery.py
py tools/inventory.py init
git config core.hooksPath .githooks
py tools/secret.py set nvidia/personal/api_key
py -m unittest discover -s tools/tests -t . -v
```

---

## Requirements

| Component | Minimum | Notes |
|-----------|---------|-------|
| Python 3 | 3.10+ | stdlib only, no venv, no pip (`py` launcher on Windows) |
| git | any recent version | for cloning and committing |
| bash | Git Bash on Windows | for shell scripts |
| An agent | latest | Claude Code, Gemini CLI, opencode or goose |
| Native credential store | KWallet, secret-tool, Keychain, WCM, TDE DCOP | for API keys |
| node.js + npm | optional | only to render diagrams (`docs/procedures/html-docs.md`) |

---

## License

MIT — see [`LICENSE`](LICENSE).
