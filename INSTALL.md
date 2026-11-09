# Install — AI-first workspace

**The easiest install:** clone this folder, run `autodiscovery.py`, add your API key, and start coding with any agent harness.

Made for a cheap laptop (4-8 GB RAM) with Windows 10/11 or Linux Mint; no local models.
Tested on **Windows 10** and **Q4OS Linux (TDE)**; Linux Mint is the next test platform.
On Windows use `py` where this page says `python3`.

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
# Check the environment (python3, git, bash, inventory db)
python3 tools/autodiscovery.py

# Create the SQLite inventory database
python3 tools/inventory.py init

# Verify everything works (tests never touch your real secret store unless
# SECRET_LIVE_TESTS=1 is set)
python3 -m unittest discover -s tools/tests -t . -v
```

### Turn on the secret check (once per clone)

```bash
git config core.hooksPath .githooks
```

From then on every `git commit` runs `tools/secret_scan.py`, which refuses a commit
that contains an API key or token (NVIDIA `nvapi-…`, `sk-…`, GitHub `ghp_…` /
`github_pat_…`, AWS `AKIA…`, Google/Gemini `AIza…`, or a literal `api_key: <value>`). The value itself is
never printed. Scan the whole tree by hand with `python3 tools/secret_scan.py --all`.

---

## 4. Add your AI provider key

The main provider is NVIDIA (free account at build.nvidia.com, about 20 free models,
see `kb/`). Gemini and ChatGPT free plans are optional and have tight limits.

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

If an old config or one of its `.bak-*` copies still holds a key in plain text, the
tools warn and show where (never the value); delete those entries or files by hand.

If a free model thinks for too long or repeats itself: press Stop (Esc), type `/init`,
then continue.

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

---

## Requirements

| Component | Minimum | Notes |
|-----------|---------|-------|
| Python 3 | 3.10+ | stdlib only, no venv, no pip (`py` launcher on Windows) |
| git | any recent version | for cloning and committing |
| bash | Git Bash on Windows | for shell scripts |
| An agent | latest | Claude Code, Gemini CLI, opencode or goose |
| Native credential store | KWallet, secret-tool, Keychain, WCM, TDE DCOP | for API keys |
| node.js + npm | optional | only for `mermaid-cli` diagrams |

---

## License

MIT — see [`LICENSE`](LICENSE).
