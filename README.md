# AI-first workspace

**Say hello first.** Open this folder with opencode and write one word in the chat —
`hi`, `здр`, `привет` — in your own language, and ask in the same line how to work with
this thing. The agent answers in the language you write in.

*Other languages: [Български](README-bg.md).*

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
- Small Python tools that collect the free NVIDIA models and connect opencode to
  them, plus a check of your machine.
- A secret check that stops you from committing a key by accident (a git hook; it
  needs Python: without Python it only warns and lets the commit through).

Models, all free: opencode's own free models (no key needed), about 20 **free NVIDIA
models** (build.nvidia.com, free account and key), and optionally the free plans of
Gemini and ChatGPT (they have tight daily limits). No paid provider is needed. A
small list of them ships in `data/models.xml` (collected from build.nvidia.com on
2026-11-08, so it ages: models come and go). A fresher list built with `tools/robota.py`
and `tools/gen_models_xml.py` can live in a folder named by `paths.kb` in `settings.json`;
when that folder has a `models.xml`, it is used instead.

## Start on Windows (3 steps)

What to install first: [`INSTALL.md`](INSTALL.md), "What the machine needs".

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

What to install first: [`INSTALL.md`](INSTALL.md), "What the machine needs".

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
literal keys of the providers they manage, but only once that key is in the OS secret
store; until then the key stays and the tool prints the command that stores it
(`python3 tools/secret.py set <path>`, which asks for the value). Keys of other providers
are only reported; `--redact-foreign` replaces them with a placeholder. Old `.bak-*`
files you delete by hand.

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
- `~/SECRETS` is the deliberate backup made by `secret.py export` (key values in plain
  text, outside the project). Move it to a flash drive; never put it into git.
- On Q4OS/TDE the wallet must be enabled and opened once by hand before `secret.py` can
  use it (`dcop` lives in `/opt/trinity/bin`; `secret.py` finds it).

## What is in the folder

```text
AGENTS.md      the rules for every agent      CLAUDE.md / GEMINI.md  pointers to AGENTS.md
INSTALL.md     step-by-step install           docs/design/ architecture and accessibility pages
tools/         small Python tools (stdlib)    lib/kikolib/ vendored secret-store library
data/          inventory schema and seed
docs/procedures/  steps for step-review, commit, release audit, HTML docs, GitHub, orchestration, new project
.claude/       Claude Code skills          .opencode/   opencode commands (both point to docs/procedures/)
out/           reports and audits (not in git)
projects/      your own projects, one folder each (not in this repo's git)
```

Tools: `secret.py` (keys), `inventory.py` (local SQLite list of machines, services,
providers, models, keys and projects), `autodiscovery.py` (machine check), `ping.py` / `ping_direct.py` (test a model),
`setup_nvidia.py` / `setup_providers.py` / `opencode_config.py` (connect opencode to providers),
`run_opencode.py` (start opencode with the keys from the OS store),
`robota.py` + `gen_models_xml.py` (refresh the model list), `secret_scan.py` (the commit and push check),
`bundle.py` (the core plus one project in a single folder, for handover).

Run the tests: `python3 -m unittest discover -s tools/tests -t . -v` (`py` on Windows).

Local settings: copy `settings.json.example` to `settings.json` (not tracked by git).
`tools` holds a full path or command per program (empty = found on PATH;
`autodiscovery.py --save` fills it in); `run_opencode.py` and `ping.py` use
`tools.opencode`. `git` holds `remote_url`, `remote_user` and `token_key` for the
GitHub steps. An older `runtime` section is still read. Key names: see INSTALL.md,
"Key names".

## Projects

Your own work goes in `projects/<name>/`, one folder per project, and each folder is its
own git repository: root at that folder, its own `AGENTS.md`, its own `docs/`, `tools/` and
its own history. `projects/` is gitignored here, so this repository never tracks client
work and its history never carries another business's names.

That is deliberate:

- a project can be copied out, handed over or sold as a bundle:
  `py tools/bundle.py <name>` puts the core and the project into one folder and runs the
  project's tests inside it;
- it can be pushed to its own remote (a client's GitHub organisation) without touching this
  repository, and this repository can be pushed without publishing the project;
- this workspace still works if a project is deleted. A project does need the core at
  runtime — it is the framework — and the bundle carries the core with it.

Record a project in the local list with `py tools/inventory.py add-project <name>`. The
whole procedure, including what must be checked before a folder is handed over:
[`docs/procedures/new-project.md`](docs/procedures/new-project.md).

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
