# Install — Portable AI Development Workspace

**The easiest install:** clone this folder, run `autodiscovery.py`, add your API key, and start coding with any agent harness.

Works on **Windows 10** and **Linux (Debian/Ubuntu/Mint/Q4OS)**.

---

## 1. Clone / unpack the project

```bash
# Option A: clone from GitHub
git clone https://github.com/peterkokosharov/ai-first-workspace.git
cd ai-first-workspace

# Option B: unpack the archive
tar xzf default-project.tar.gz
cd Default Project
```

---

## 2. Install OpenCode

OpenCode is the primary agent harness for this project.

### Linux (Debian / Ubuntu / Mint / Q4OS)

```bash
# Option A: npm (if you have node.js)
npm install -g @opencode/opencode

# Option B: download binary from GitHub releases
# https://github.com/opencode-ai/opencode/releases
```

### Windows 10

Install **Git Bash** first (from https://git-scm.com/), then:

```bash
# In Git Bash
npm install -g @opencode/opencode
```

Or download the OpenCode Windows binary from GitHub releases and add it to `PATH`.

---

## 3. Install the workspace

```bash
# Check the environment (python3, git, bash, inventory db)
python3 tools/autodiscovery.py

# Create the SQLite inventory database
python3 tools/inventory.py init

# Verify everything works
python3 -m unittest discover -s tools/tests -t . -v
# Expected: 69 tests, all OK (1 skipped — live DCOP needs SECRET_LIVE_TESTS=1)
```

---

## 4. Add your AI provider key

Choose **one** provider and add its key to your OS native credential store:

```bash
# NVIDIA Nemotron (free tier)
python3 tools/secret.py --backend auto set nvidia/personal/api_key

# Gemini
python3 tools/secret.py --backend auto set gemini/personal/api_key

# Groq
python3 tools/secret.py --backend auto set groq/personal/api_key

# OpenRouter
python3 tools/secret.py --backend auto set openrouter/personal/api_key
```

The value is read from **prompt/stdin** — never printed.

---

## 5. Run OpenCode

```bash
opencode run -m nemotron-ultra --format json "hi"
```

Or start an interactive session:

```bash
opencode run -m nemotron-ultra
```

---

## 6. Run Goose CLI (optional)

Goose is an alternative AI agent CLI included in `test-env/`:

```bash
cd ~/test-env
./bin/goose configure
# Provider: litellm
# LITELLM_API_KEY: your nvidia/gemini/groq key
# LITELLM_HOST: http://127.0.0.1:8000
# Model: nvidia/nemotron-ultra

./bin/goose session --name my-session
```

---

## 7. Run Claude Code CLI (optional)

If you have Claude Code installed, use the wrapper in `test-env/`:

```bash
cd ~/test-env
./run-claude.sh
```

It routes through `litellm` on `http://127.0.0.1:8000/v1`.

---

## Quick start (one-liner summary)

```bash
git clone https://github.com/peterkokosharov/ai-first-workspace.git
cd ai-first-workspace
python3 tools/autodiscovery.py
python3 tools/inventory.py init
python3 tools/secret.py --backend auto set nvidia/personal/api_key
python3 -m unittest discover -s tools/tests -t . -v
opencode run -m nemotron-ultra --format json "hi"
```

---

## Requirements

| Component | Minimum | Notes |
|-----------|---------|-------|
| Python 3 | 3.10+ | stdlib only, no venv, no pip |
| git | any recent version | for cloning and committing |
| bash | Git Bash on Windows | for shell scripts |
| OpenCode | latest | primary agent harness |
| Native credential store | KWallet, secret-tool, Keychain, WCM, TDE DCOP | for API keys |
| node.js + npm | optional | only for `mermaid-cli` diagrams |

---

## License

MIT License. See `LICENSE`.
