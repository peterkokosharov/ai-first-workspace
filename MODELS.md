# MODELS — модели и ключове

Списък на моделите, с които разполагаме, и кой ключ използва всеки от тях.
Файлът съдържа **само имена** — стойностите на ключовете са във файла `~/SECRETS`
(извън проекта).

## Модели

| Модел | Услуга | Ключ |
|---|---|---|
| `gemini/gemini-3.5-flash-lite` | gemini | `GEMINI_API_KEY` |
| `gemini/gemini-3.8-flash` | gemini | `GEMINI_API_KEY` |
| `nvidia/nemotron-3-ultra-550b-a55b` | nvidia | `NVIDIA_API_KEY` |
| `nvidia/nemotron-3-super-120b-a12b` | nvidia | `NVIDIA_API_KEY` |
| `groq/llama-3.3-70b-versatile` | groq | `GROQ_API_KEY` |
| `openrouter/qwen/qwen3.8-27b:free` | openrouter | `OPENROUTER_API_KEY` |
| `deepseek-chat` | deepseek | `DEEPSEEK_API_KEY` |
| `mistral/mistral-small-latest` | mistral | `MISTRAL_API_KEY` |

Общо: **8 модела** с **6 ключа** за услуги (седмият ключ е `GITHUB_TOKEN` за GitHub).

## Ключове

| Ключ | Услуга |
|---|---|
| `GITHUB_TOKEN` | github |
| `GEMINI_API_KEY` | gemini |
| `NVIDIA_API_KEY` | nvidia |
| `GROQ_API_KEY` | groq |
| `OPENROUTER_API_KEY` | openrouter |
| `DEEPSEEK_API_KEY` | deepseek |
| `MISTRAL_API_KEY` | mistral |

## Правила

- Стойностите се пазят само в `~/SECRETS` с формат `KEY_NAME | service | value`.
- Този файл и `KEYS` не съдържат тайни и могат да влизат в git.
- На друга машина `~/SECRETS` се създава наново; тук не се променя нищо.
- При добавяне на модел се добавят ред в таблицата по-горе и, ако е нова услуга,
  нов ключ в `~/SECRETS` и в `KEYS`.
