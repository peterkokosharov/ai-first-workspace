# kb/ — Knowledge Base: NVIDIA build.nvidia.com Free Models

This folder contains scraped information about NVIDIA NIM models that advertise a **free endpoint** usable with a free `NVIDIA_API_KEY`. It was scraped from https://build.nvidia.com/models (pages 1–5) using `tools/robota.py`.

## Folder layout

```
kb/
├── free_endpoints_index.md   # Markdown table of everything found by the scrape (includes duplicate rows)
├── models.xml                # XML: the de-duplicated model list (source of truth; used by tools/setup_nvidia.py)
├── md/                       # Markdown export per model
├── html/                     # Raw detail-page HTML
└── config.yaml               # OPTIONAL example for a LiteLLM proxy; nothing in tools/ reads it
```

## How the data was collected

1. `tools/robota.py` fetches `https://build.nvidia.com/models?page=1..5`
2. For each model card on the listing page, it visits the detail page
3. It checks for:
   - "free endpoint" text → model is free-tier
   - no "API access not available" / "not open for programmatic access" notice → skip
   - looks like an LLM (chat/completions or LLM keywords)
4. It saves raw HTML to `kb/html/` and extracts title/endpoint/specs to `kb/md/`
5. `tools/gen_models_xml.py` converts `kb/free_endpoints_index.md` → `kb/models.xml`

## How to get API keys

You need an API key for the provider you want to use. All keys are stored in your OS native credential store (never in git). See `tools/secret.py` for how to set them.

| Provider | Key path in inventory | Where to get it | Cost |
|----------|----------------------|-----------------|------|
| NVIDIA | `nvidia/personal/api_key` | https://build.nvidia.com (free tier) | Free tier |
| Gemini | `gemini/personal/api_key` | https://aistudio.google.com/apikey | Free tier (60 req/min) |
| Groq | `groq/personal/api_key` | https://console.groq.com/keys | Free tier |
| OpenRouter | `openrouter/personal/api_key` | https://openrouter.ai/keys | Free tier |
| DeepSeek | `deepseek/personal/api_key` | https://platform.deepseek.com/api_keys | Paid (cheap) |
| Mistral | `mistral/personal/api_key` | https://console.mistral.ai/ | Paid (cheap) |
| Anthropic | `anthropic/personal/api_key` | https://console.anthropic.com/ | Paid |

Set a key:

```bash
python3 tools/secret.py set nvidia/personal/api_key
# the value is read from a prompt, never printed
```

`--backend file` is only for headless machines without a keyring (own user, 0600 files in ~).

Then test:

```bash
python3 tools/ping_direct.py nvidia "hi"
```

## Free models (verified working)

The models listed in `models.xml` (the source of truth; the table below is the same list) were scraped from build.nvidia.com and verified to answer on `https://integrate.api.nvidia.com/v1/chat/completions`:

| # | Alias | Full name | Endpoint |
|---|-------|-----------|----------|
| 1 | mistral-large-4-1t-a52b | Mistral Large 4 Model by Mistral AI | https://integrate.api.nvidia.com/v1/chat/completions |
| 2 | nemotron-3-5-bolt-e4b | Nemotron 3.5 Bolt E4B Model by NVIDIA | https://integrate.api.nvidia.com/v1/chat/completions |
| 3 | minimax-m3.1-flash | minimax-m3.1-flash Model by Minimaxai | https://integrate.api.nvidia.com/v1/chat/completions |
| 4 | nemotron-3-5-super-vl-120b-a12b | nemotron-3.5-super-vl-120b-a12b Model by NVIDIA | https://integrate.api.nvidia.com/v1/chat/completions |
| 5 | step-5-preview | Step 5 Preview Model by Stepfun-ai | https://integrate.api.nvidia.com/v1/chat/completions |
| 6 | deepseek-v4.1-flash | deepseek-v4.1-flash Model by Deepseek-ai | https://integrate.api.nvidia.com/v1/chat/completions |
| 7 | glm-5-3-flash | glm-5-3-flash Model by Z-ai | https://integrate.api.nvidia.com/v1/chat/completions |
| 8 | nemotron-parse-2.0 | nemotron-parse-2.0 Model by NVIDIA | https://integrate.api.nvidia.com/v1/chat/completions |
| 9 | nemotron-3-5-lightning-30b-a3b | nemotron-3.5-lightning-30b-a3b Model by NVIDIA | https://integrate.api.nvidia.com/v1/chat/completions |
| 10 | muse-glimmer-30b | muse-glimmer-30b Model by Meta | https://integrate.api.nvidia.com/v1/chat/completions |
| 11 | riva-translate-4b-instruct-v2 | riva-translate-4b-instruct-v2 Model by NVIDIA | https://integrate.api.nvidia.com/v1/chat/completions |
| 12 | ising-calibration-1.5-31b | ising-calibration-1.5-31b Model by NVIDIA | https://integrate.api.nvidia.com/v1/chat/completions |
| 13 | laguna-xs-2.1 | laguna-xs-2.1 Model by Poolside | https://integrate.api.nvidia.com/v1/chat/completions |
| 14 | diffusiongemma-26b-a4b-it | diffusiongemma-26b-a4b-it Model by Google | https://integrate.api.nvidia.com/v1/chat/completions |
| 15 | nemotron-3-ultra-550b-a55b | nemotron-3-ultra-550b-a55b Model by NVIDIA | https://integrate.api.nvidia.com/v1/chat/completions |
| 16 | nemotron-3-5-content-safety | nemotron-3.5-content-safety Model by NVIDIA | https://integrate.api.nvidia.com/v1/chat/completions |
| 17 | nemotron-3-nano-omni-30b-a3b-reasoning | nemotron-3-nano-omni-30b-a3b-reasoning Model by NVIDIA | https://integrate.api.nvidia.com/v1/chat/completions |
| 18 | nemotron-parse | nemotron-parse Model by NVIDIA | https://integrate.api.nvidia.com/v1/chat/completions |
| 19 | llama-3-1-nemotron-safety-guard-8b-v3 | llama-3.1-nemotron-safety-guard-8b-v3 Model by NVIDIA | https://integrate.api.nvidia.com/v1/chat/completions |
| 20 | gpt-oss-20b | gpt-oss-20b Model by OpenAI | https://integrate.api.nvidia.com/v1/chat/completions |
| 21 | llama-guard-4-12b | llama-guard-4-12b Model by Meta | https://integrate.api.nvidia.com/v1/chat/completions |
| 22 | llama-3-1-nemoguard-8b-topic-control | llama-3.1-nemoguard-8b-topic-control Model by NVIDIA | https://integrate.api.nvidia.com/v1/chat/completions |
| 23 | llama-3-1-nemoguard-8b-content-safety | llama-3.1-nemoguard-8b-content-safety Model by NVIDIA | https://integrate.api.nvidia.com/v1/chat/completions |

> Some of these are safety/guard models (`llama-guard-*`, `nemotron-3-5-content-safety`, `nemotron-parse`). They answer but may refuse certain prompts.

## How to configure OpenCode providers

Use `tools/setup_providers.py`:

```bash
python3 tools/setup_providers.py gemini
python3 tools/setup_providers.py nvidia
python3 tools/setup_providers.py groq
python3 tools/setup_providers.py deepseek
python3 tools/setup_providers.py mistral
python3 tools/setup_providers.py openrouter
```

This reads keys from KWallet (via `tools/secret.py`) and writes them into `~/.configtde/opencode/opencode.jsonc`.

## How to ping a model

```bash
# NVIDIA free model
python3 tools/ping_direct.py nvidia nemotron-3-5-bolt-e4b "hi"

# Groq free model
python3 tools/ping_direct.py groq/llama "hi"

# Direct OpenCode (if configured)
opencode run -m nvidia/nemotron-ultra --format json "hi"
```

## How to re-scrape

If build.nvidia.com adds new models, re-run:

```bash
python3 tools/robota.py --pages 1-5
python3 tools/gen_models_xml.py
```

This overwrites `kb/html/`, `kb/md/`, `kb/free_endpoints_index.md` and `kb/models.xml`.

---

## License

MIT License — same as the rest of the project. See `LICENSE` in project root.

---

**Note:** `kb/` is part of the git repository. Do not commit API keys here. `data/inventory.db` is gitignored and never committed. `~/.litellm/env` and `~/.kiko/.env` are outside the project and must not be committed.
