# oc-connnector-free-models

Portable project: connect OpenCode to all free NVIDIA NIM models
scraped from https://build.nvidia.com/models (pages 1–5).

## What it does

`tools/setup_nvidia.py` reads `kb/models.xml` (23 models scraped from
build.nvidia.com) and writes `~/.configtde/opencode/opencode.jsonc`
with one provider entry per model, using key `nvidia/personal/api_key`
from `data/inventory.db` via `tools/secret.py`.

After running, restart OpenCode. All 23 free models appear in the
model listbox:

- mistralai/mistral-large-4-1t-a52b
- nvidia/nemotron-3.5-bolt-e4b
- minimaxai/minimax-m3.1-flash
- nvidia/nemotron-3.5-super-vl-120b-a12b
- stepfun-ai/step-5-preview
- deepseek-ai/deepseek-v4.1-flash
- z-ai/glm-5-3-flash
- nvidia/nemotron-parse-2.0
- nvidia/nemotron-3.5-lightning-30b-a3b
- meta/muse-glimmer-30b
- nvidia/riva-translate-4b-instruct-v2
- nvidia/ising-calibration-1.5-31b
- poolside/laguna-xs-2.1
- google/diffusiongemma-26b-a4b-it
- nvidia/nemotron-3-ultra-550b-a55b
- nvidia/nemotron-3.5-content-safety
- nvidia/nemotron-3-nano-omni-30b-a3b-reasoning
- nvidia/nemotron-parse
- nvidia/llama-3_1-nemotron-safety-guard-8b-v3
- openai/gpt-oss-20b
- meta/llama-guard-4-12b
- nvidia/llama-3_1-nemoguard-8b-topic-control
- nvidia/llama-3_1-nemoguard-8b-content-safety

## Prerequisites

- Python 3.x
- `data/inventory.db` created via `python3 tools/inventory.py init`
- Secret `nvidia/personal/api_key` set via:
    ```
    python3 tools/secret.py --backend auto set nvidia/personal/api_key
    ```
- OpenCode installed and configured

## Usage

```bash
cd /home/petark/Documents/Default Project/projects/oc-connnector-free-models
python3 tools/setup_nvidia.py
```

Then restart OpenCode. All 23 models appear in the model listbox as
OpenAI-compatible providers pointing at
`https://integrate.api.nvidia.com/v1/chat/completions`.

## Test

```bash
python3 tools/ping_direct.py nvidia nemotron-3-5-bolt-e4b "hi"
python3 tools/ping_direct.py nvidia mistral-large-4-1t-a52b "hi"
```

## Files

- `tools/setup_nvidia.py` — writes OpenCode config from kb/models.xml
- `kb/models.xml` — 23 models scraped from build.nvidia.com
- `kb/free_endpoints_index.md` — index table
- `kb/md/` — Markdown per model
- `kb/html/` — raw HTML from build.nvidia.com
