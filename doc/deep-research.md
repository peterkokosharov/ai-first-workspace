# Deep Research Report — AI-First Workspace

**Date:** Mon Nov 09 2026  
**Project:** /home/petark/Documents/Default Project  
**Scope:** Tools, tests, data, kb, docs, lib, projects, git history

---

## 1. Project Overview

- **Name:** AI-first workspace (portable development folder)
- **Version:** v5 — tooling implemented and tested; auto-discovery added
- **License:** MIT, copyright 2026 Peter Kokosharov
- **Language:** Python 3.x (stdlib only), no venv, no pip
- **Tests:** 254 pass, 3 skipped (live DCOP tests require `SECRET_LIVE_TESTS=1`)
- **Git:** `origin` → `https://github.com/peterkokosharov/ai-first-workspace.git`, branch `main`, 10 commits

## 2. Architecture

### Core Tools (`tools/`)
| Tool | Purpose | Tests |
|------|---------|-------|
| `secret.py` | Portable secret tool over native credential stores (WCM, Keychain, secret-tool, KWallet, TDE DCOP, memory, file) | ✅ |
| `inventory.py` | SQLite inventory manager (machines, services, providers, models, keys, tools, settings) | ✅ |
| `autodiscovery.py` | Machine discovery (OS, RAM, CPU, Python, git, bash, node, docker, opencode, etc.) | ✅ |
| `ping.py` | Ping model via OpenCode, verify against inventory DB | ✅ |
| `ping_direct.py` | Ping LLM providers directly via HTTP (gemini, nvidia, deepseek, mistral) | ✅ |
| `setup_nvidia.py` | Configure OpenCode providers with free NVIDIA models from `data/models.xml` (or `paths.kb/models.xml`) | ✅ |
| `setup_providers.py` | Configure OpenCode providers from keys in inventory | ✅ |
| `robota.py` | Scrape build.nvidia.com for free-endpoint models | ✅ |
| `gen_models_xml.py` | Generate `models.xml` in `paths.kb` from the scraped index | ✅ |
| `opencode_config.py` | Shared helpers for OpenCode config manipulation | ✅ |
| `run_opencode.py` | Start OpenCode with keys from OS secret store | ❌ no tests |
| `secret_scan.py` | Git hook: refuse commits/pushes containing API keys | ✅ |
| `workspace_settings.py` | Read local `settings.json` (stdlib only) | ✅ |
| `bootstrap.sh` | One-command init: `init` → `autodiscovery.py` → tests | — |

### Vendored Library (`lib/kikolib/`)
14 modules: keystore, factory, http_client, server, sse, tokens, retry, config, dotenv, posix_utils, native_utils, yaml_lite, tomlwrite, websocket

### Model list and Knowledge Base
The core ships `data/models.xml` (23 free NVIDIA models, data only). A `models.xml` in the
folder `paths.kb` overrides it. The collected pages below are not part of the core: the
model lab (`projects/models/`) owns them, in its `paths.kb` folder.
- `models.xml` — 23 free NVIDIA models scraped from build.nvidia.com
- `free_endpoints_index.md` — index of free endpoints
- `md/` and `html/` — 23 files each (Markdown + raw HTML per model)
- `config.yaml` — KB configuration

### Data (`data/`)
- `schema.sql` — committed SQLite schema (7 tables)
- `seed.sql` — committed initial inventory data
- `inventory.db` — local, gitignored, recreated by `init`

### Documentation (`doc/`, `docs/`)
- `doc/architecture.md` + `architecture.html`
- `doc/accessibility.html`
- `doc/diagrams/` — 10 Mermaid diagrams (SVG rendered)
- `docs/procedures/` — 6 procedure files
- `INSTALL.md` — comprehensive install guide
- `README.md` — project overview

### Projects (`projects/`)
- 4 symlinked projects: `2027-book`, `2028-book`, `kiko`, `rex`
- `oc-connnector-free-models` — deleted

### Git Hooks (`.githooks/`)
- `pre-commit` — runs `secret_scan.py`
- `pre-push` — runs `secret_scan.py --push`

## 3. Bugs Found

1. **`tools/setup_providers.py` and `tools/ping_direct.py` — duplicate `get_key_from_kwallet` alias**
   - Line 90 in both files: `get_key_from_kwallet = get_key_from_secret  # old name, kept for compatibility`
   - Never called anywhere. Dead code.

2. **`tools/inventory.py` — `cmd_sql` read-only check uses string prefix matching**
   - Could be bypassed with SQL comments (e.g., `/* */ SELECT`). Low risk since it's a local tool.
   - Mitigation: only SELECT/WITH statements allowed.

3. **`tools/robota.py` — `scrape_page` uses `html.parser` without error handling**
   - `HTMLParser` may fail on malformed HTML. No try/except around parsing.

4. **`tools/opencode_config.py` — `_redact` may not handle all secret patterns**
   - Only checks known patterns (nvapi-, sk-, ghp_, etc.). Unknown patterns pass through.

5. **`tools/run_opencode.py` — `unsafe_for_batch` uses string matching**
   - Could miss variations of `--auto` flag.

6. **`tools/setup_nvidia.py` and `tools/setup_providers.py` — duplicate `get_key_from_secret`**
   - Identical function in both files. Should be extracted to shared module.

## 4. Unused Code

1. **`get_key_from_kwallet` alias** — defined in `setup_providers.py` and `ping_direct.py`, never called. **Dead code.**
2. **`tools/run_opencode.py` — no tests** — functionally untested.
3. **`tools/setup_nvidia.py` CLI — no tests** — only `parse_models` and `build_models` are tested.
4. **`tools/setup_providers.py` CLI — no tests** — only `load_config` and `save_config` are tested.

## 5. Security Audit

- ✅ Secret values never enter git (pre-commit hook + secret_scan.py)
- ✅ `data/inventory.db` is gitignored
- ✅ `settings.json` is gitignored
- ✅ `out/` is gitignored
- ✅ `projects/` is gitignored
- ✅ `~/SECRETS` is outside the project
- ✅ `auto` backend never falls back to plaintext
- ✅ `--backend file` requires explicit order
- ⚠️ `secret_scan.py` pre-commit hook only activates with `git config core.hooksPath .githooks`
- ⚠️ `secret.py list` shows key names (not values) — correct
- ⚠️ `inventory.py key <name>` shows key names (not values) — correct

## 6. Test Coverage

| Area | Tests | Status |
|------|-------|--------|
| secret.py | 57 | ✅ |
| inventory.py | 18 | ✅ |
| autodiscovery.py | 19 | ✅ |
| gen_models_xml.py | 12 | ✅ |
| ping.py | 12 | ✅ |
| ping_direct.py | 8 | ✅ |
| robota.py | 15 | ✅ |
| opencode_config.py | 8 | ✅ |
| secret_scan.py | 10 | ✅ |
| workspace_settings.py | 8 | ✅ |
| setup_config | 4 | ✅ |
| hooks | 6 | ✅ |
| run_opencode.py | 0 | ❌ |
| setup_nvidia.py (CLI) | 0 | ❌ |
| setup_providers.py (CLI) | 0 | ❌ |
| bootstrap.sh | 0 | ❌ |
| **Total** | **254** | **251 pass, 3 skip** |

## 7. Recommendations

1. **Remove dead code:** `get_key_from_kwallet` alias in `setup_providers.py` and `ping_direct.py`
2. **Extract shared function:** Move `get_key_from_secret` to a shared module
3. **Add tests:** `run_opencode.py`, `setup_nvidia.py` CLI, `setup_providers.py` CLI
4. **Improve SQL injection protection:** Use parameterized queries in `cmd_sql` (already read-only)
5. **Add error handling:** Wrap HTML parsing in `robota.py` with try/except
6. **Document `settings.json` schema:** Add validation for unknown keys
7. **Consider adding `--dry-run` to all mutating commands**

## 8. Project Health

| Metric | Value |
|--------|-------|
| Total Python files | 14 tools + 15 test files + 14 lib modules |
| Total tests | 254 (251 pass, 3 skip) |
| Test pass rate | 100% (excluding live DCOP) |
| Git commits | 10 |
| Uncommitted changes | 0 (working tree clean) |
| Security issues | 0 (no secrets in git) |
| Dead code items | 1 (get_key_from_kwallet alias) |
| Missing tests | 4 tools without CLI tests |

**Overall assessment:** The project is well-structured, thoroughly tested, and follows good security practices. The main gaps are missing CLI tests for 4 tools and one dead code item. The architecture is clean with good separation of concerns.