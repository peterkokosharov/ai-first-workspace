# AI-first workspace

**What it is:** a ready-made folder for writing a program (or a book) together with an
AI agent, for **$0**. Download the folder, open it with **opencode** and its free
models, and the agent finds its rules, tools and model list inside. Copy the folder to
another computer and work continues there.

**Who it is for:** anyone, including beginners, with a cheap laptop (4-8 GB RAM,
Windows 10/11 or Linux Mint). Nothing runs a model locally, so little RAM is enough;
the models run in the cloud on free tiers.

**What you get:**

- Rules the agent follows (`AGENTS.md`), so every agent behaves the same way.
- A safe place for API keys: the key stays in the operating system's own secret store
  (Windows Credential Manager, KWallet, GNOME Keyring), never in a file in this folder.
- A list of free models you can use (`kb/`), plus small tools to check your machine,
  store keys and connect opencode to the models.
- A secret check that stops you from committing a key by accident (a git hook; it
  needs Python: without Python it only warns and lets the commit through).

Models, all free: opencode's own free models (no key needed), about 20 **free NVIDIA
models** (build.nvidia.com, free account and key), and optionally the free plans of
Gemini and ChatGPT (they have tight daily limits). No paid provider is needed. The
model list lives in [`kb/`](kb/README.md); it was collected from build.nvidia.com with
`tools/robota.py` on 2026-11-08, so it ages: models come and go.

## Start on Windows (3 steps)

1. Install **Python 3.10 or newer** from python.org (it brings the `py` launcher) and **Git for
   Windows** (it brings Git Bash). Install **opencode** (https://opencode.ai).
2. Get this folder (`git clone https://github.com/peterkokosharov/ai-first-workspace.git`
   or unzip it), open **Git Bash** in it and run:
   ```bash
   py tools/autodiscovery.py      # checks your machine
   py tools/inventory.py init     # creates the local list of tools and models
   git config core.hooksPath .githooks   # turns on the secret check
   ```
3. Start opencode in the folder; its free models work without a key. Optional: store a
   free NVIDIA key (it goes into Windows Credential Manager; you type it, it is never
   shown) for more models:
   ```bash
   opencode
   py tools/secret.py set nvidia/personal/api_key     # optional
   ```

## Start on Linux (3 steps)

Target: Linux Mint (Cinnamon), which keeps keys in GNOME Keyring through `secret-tool`
(package `libsecret-tools`, usually already there). Tested so far on Q4OS (TDE, KWallet).

1. Make sure `python3` (3.10 or newer) and `git` are installed (`python3 --version`, `git --version`).
   Install **opencode** (https://opencode.ai).
2. Get this folder and run in it:
   ```bash
   python3 tools/autodiscovery.py
   python3 tools/inventory.py init
   git config core.hooksPath .githooks
   ```
3. Start opencode in the folder; its free models work without a key. Optional: store a
   free NVIDIA key (the desktop's keyring is picked automatically) for more models:
   ```bash
   opencode
   python3 tools/secret.py set nvidia/personal/api_key     # optional
   ```

More detail: [`INSTALL.md`](INSTALL.md).

## Agents

opencode is the default because it is free. The others also work with this folder.

| Agent | Status | Reads the rules from |
|-------|--------|----------------------|
| opencode | tested (default, free models) | `AGENTS.md` |
| Gemini CLI | tested (free plan with limits) | `GEMINI.md` (which points to `AGENTS.md`) |
| goose | tested | `AGENTS.md` |
| Claude Code | tested (needs a paid plan) | `CLAUDE.md` (which points to `AGENTS.md`) |
| Codex CLI | not tested | `AGENTS.md` |

## Connect opencode to the NVIDIA models (optional)

```bash
python3 tools/setup_nvidia.py --dry-run   # shows what would change, writes nothing
python3 tools/setup_nvidia.py             # adds the NVIDIA models to opencode's config
python3 tools/run_opencode.py             # start opencode WITH your stored keys
```

(`py` instead of `python3` on Windows.) The key is **never written to opencode's
config**: the config only names the variable `NVIDIA_API_KEY`. Start opencode through
`tools/run_opencode.py`: it reads your keys from the OS secret store and hands them to
the opencode process only (not to your shell, not to a file). All arguments go on to
opencode, e.g. `python3 tools/run_opencode.py run -m nvidia/<model> 'hi'`. Plain
`opencode` still works for opencode's own free models. Other providers (Gemini,
DeepSeek, Groq, Mistral, OpenRouter): `python3 tools/setup_providers.py <name>`.

If an old config (or one of its `.bak-*` copies, or `./opencode.json` in the current
folder) still contains a key in plain text, the tools warn and show where, never the
value. The setup tools remove the entries that older versions wrote (one per model) and
redact other literal keys in the config they write; old `.bak-*` files you delete by hand.

The keys live in opencode's environment, so programs that opencode starts (shell
commands, agent tools) can read them too. An agent must never print environment
variables (`env`, `set`, `printenv`, `echo $NVIDIA_API_KEY`).

The setup tools are safe to re-run: they need no admin rights (no sudo), change nothing
outside your user folder, and copy the old config unchanged to
`<file>.bak-YYYYMMDD-HHMMSS-ffffff` before writing (readable only by you on Linux/macOS;
default permissions on Windows). If that copy holds a plain-text key, the tool says so:
delete the copy once the key is in the OS secret store. opencode's documentation names
`~/.config/opencode/opencode.json` as the global config; the tools use that folder on
Linux and on Windows (`%USERPROFILE%\.config\opencode`). **Unverified on Windows:**
the docs give no Windows-specific path and this was not tested with a real opencode
install on Windows; if your opencode reads another folder, set `OPENCODE_CONFIG` to that
file so the tools write there (the config page does not document this variable). Also `$XDG_CONFIG_HOME/opencode` if that is set, and `~/.configtde/opencode` only
inside a TDE session.

## If the model loops

Free models such as **Big Pickle** (opencode) or **Nemotron Super** sometimes think for
a very long time or repeat themselves. Then:

1. Press **Stop** (Esc in most terminal agents).
2. Type `/init` and send it.
3. Continue with your task.

## Secrets

- Key values never enter git, the archive or any project file.
- The store is the operating system's own: Windows Credential Manager, macOS Keychain,
  GNOME Keyring (`secret-tool`), KWallet, or the TDE wallet (DCOP) on Q4OS.
  `tools/secret.py` picks it automatically and never falls back to a plain file.
- `~/SECRETS` is only a temporary transfer file outside the project (for moving keys to
  a new machine); delete it after import.
- On Q4OS/TDE the wallet must be enabled and opened once by hand before `secret.py` can
  use it (`dcop` lives in `/opt/trinity/bin`; `secret.py` finds it).

## What is in the folder

```text
AGENTS.md      the rules for every agent      CLAUDE.md / GEMINI.md  pointers to AGENTS.md
INSTALL.md     step-by-step install           kb/          the free model list
tools/         small Python tools (stdlib)    lib/kikolib/ vendored secret-store library
data/          inventory schema and seed      doc/         architecture and accessibility pages
docs/procedures/  steps for review, commit, release audit, HTML docs, GitHub, orchestration
projects/      your own projects, one folder each (not in this repo's git)
```

Tools: `secret.py` (keys), `inventory.py` (local SQLite list of machines, providers,
models), `autodiscovery.py` (machine check), `ping.py` / `ping_direct.py` (test a model),
`setup_nvidia.py` / `setup_providers.py` (connect opencode to providers),
`run_opencode.py` (start opencode with the keys from the OS store),
`robota.py` + `gen_models_xml.py` (refresh `kb/`), `secret_scan.py` (the commit check).

Run the tests: `python3 -m unittest discover -s tools/tests -t . -v` (`py` on Windows).

Local settings: `settings.json.example` lists the program names `autodiscovery.py`
looks for. To change one, copy it to `settings.json` (not tracked by git) and edit the copy.

## Optional example — local model proxy

Not needed to start. One test machine ran a local OpenAI-compatible proxy (for example
LiteLLM on `http://127.0.0.1:8000/v1`) as a user service in front of the free NVIDIA
models. The workspace does not install or require it. If you run one, keep its keys in
the OS secret store (`tools/secret.py`), never in a file inside this folder.

## Move to another machine

1. Copy or clone the folder.
2. Run `autodiscovery.py` and `inventory.py init` as in the start steps.
3. Store the keys again with `secret.py set ...` (or import `~/SECRETS`, then delete it).
4. Start your agent.

## License

MIT — see [`LICENSE`](LICENSE).
