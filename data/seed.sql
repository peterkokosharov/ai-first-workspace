-- Initial inventory data.  Committed to git and safe to re-run: every statement is
-- INSERT OR IGNORE, so user edits in data/inventory.db are not overwritten.
-- Values of secrets are never recorded here; only key paths.
-- No machine rows: "python3 tools/autodiscovery.py --save" records this machine in the
-- local database. Your own services and keys: inventory.py add-service / add-key.
--
-- Key names for per-project tokens: scope/project/kind, scope = personal | company
-- (e.g. personal/my-project/github_token). Model provider keys keep their names
-- (e.g. nvidia/personal/api_key).

INSERT OR REPLACE INTO schema_meta (key, value) VALUES ('schema_version', '3');

INSERT OR IGNORE INTO services (id, name, kind, account, status, notes) VALUES
    (1, 'github', 'code hosting', 'personal', 'active', NULL),
    (2, 'gmail', 'mail', 'personal', 'active', NULL),
    (3, 'facebook', 'social', NULL, 'unknown', 'to clarify'),
    (4, 'jira', 'issue tracking', NULL, 'planned', NULL),
    (5, 'confluence', 'documentation', NULL, 'planned', NULL);

INSERT OR IGNORE INTO providers (id, name, kind, base_url, free_tier, status, notes) VALUES
    (1, 'gemini',   'llm', NULL, 1, 'active', 'free tier: gemini-3.5-flash-lite, gemini-3.8-flash'),
    (2, 'nvidia',   'llm', NULL, 0, 'active', 'direct endpoint works'),
    (3, 'opencode', 'llm', NULL, 1, 'active', 'free models, no key'),
    (4, 'groq',     'llm', NULL, 0, 'active', NULL),
    (5, 'openrouter', 'llm', NULL, 0, 'active', NULL),
    (6, 'deepseek', 'llm', NULL, 0, 'active', NULL),
    (7, 'mistral',  'llm', NULL, 0, 'active', NULL),
    (8, 'anthropic','llm', NULL, 0, 'active', 'claude: 12-15 models'),
    (9, 'codex',    'llm', NULL, 1, 'active', 'free tier: several GPT models'),
    (10, 'litellm', 'llm', NULL, 1, 'active', 'optional local LiteLLM proxy'),
    (11, 'kiko',    'llm', NULL, 1, 'active', 'kiko proxy integration'),
    (12, 'goose',   'llm', NULL, 0, 'unknown', 'integration unknown'),
    (13, 'rez',     'llm', NULL, 1, 'active', 'rez integrated with kiko');

INSERT OR IGNORE INTO keys (id, path, service_id, provider_id, kind, status, notes) VALUES
    -- GitHub tokens are stored in the OS store by git's credential helper (see
    -- docs/procedures/github-deploy.md); the rows only name them.
    (1, 'personal/my-project/github_token', 1, NULL, 'github_token', 'active',
        'managed by git credential helper, not secret.py'),
    (2, 'company/prj1/github_token', 1, NULL, 'github_token', 'planned',
        'managed by git credential helper, not secret.py'),
    (3, 'company/prj2/github_token', 1, NULL, 'github_token', 'planned',
        'managed by git credential helper, not secret.py'),
    (4, 'gemini/personal/api_key', NULL, 1, 'api_key', 'active', NULL),
    (5, 'nvidia/personal/api_key', NULL, 2, 'api_key', 'active', NULL),
    (6, 'groq/personal/api_key', NULL, 4, 'api_key', 'active', NULL),
    (7, 'openrouter/personal/api_key', NULL, 5, 'api_key', 'active', NULL),
    (8, 'deepseek/personal/api_key', NULL, 6, 'api_key', 'active',
        'placeholder value, not a real key yet'),
    (9, 'mistral/personal/api_key', NULL, 7, 'api_key', 'active', NULL),
    (10, 'anthropic/personal/api_key', NULL, 8, 'api_key', 'planned', 'claude models'),
    (11, 'codex/personal/api_key', NULL, 9, 'api_key', 'planned', 'codex GPT models'),
    (12, 'litellm/personal/api_key', NULL, 10, 'api_key', 'planned', 'optional local proxy'),
    (13, 'kiko/personal/api_key', NULL, 11, 'api_key', 'planned', 'kiko proxy'),
    (14, 'rez/personal/api_key', NULL, 13, 'api_key', 'planned', 'rez integrated with kiko'),
    (15, 'personal/gmail/app_password', 2, NULL, 'app_password', 'planned',
        'no value until you store one with tools/secret.py set');

INSERT OR IGNORE INTO models (id, alias, model_id, provider_id, key_id, tier, context_window, cost_per_1k, status, notes) VALUES
    -- Gemini (free tier)
    (1, 'gemini-flash-lite', 'gemini/gemini-3.5-flash-lite', 1, 4, 'free', 1048576, NULL, 'active', NULL),
    (2, 'gemini-flash', 'gemini/gemini-3.8-flash', 1, 4, 'free', 1048576, NULL, 'active', NULL),
    -- NVIDIA (paid)
    (3, 'nemotron-ultra', 'nvidia/nemotron-3-ultra-550b-a55b', 2, 5, 'paid', NULL, NULL, 'active',
        'direct NVIDIA endpoint works'),
    -- NVIDIA build.nvidia.com free endpoints (chat/completions, free NVIDIA_API_KEY)
    (35, 'mistral-large-4-1t-a52b', 'mistralai/mistral-large-4-1t-a52b', 2, 5, 'free', NULL, NULL, 'active', NULL),
    (36, 'nemotron-3-5-bolt-e4b', 'nvidia/nemotron-3.5-bolt-e4b', 2, 5, 'free', NULL, NULL, 'active', NULL),
    (37, 'minimax-m3.1-flash', 'minimaxai/minimax-m3.1-flash', 2, 5, 'free', NULL, NULL, 'active', NULL),
    (38, 'nemotron-3-5-super-vl-120b-a12b', 'nvidia/nemotron-3.5-super-vl-120b-a12b', 2, 5, 'free', NULL, NULL, 'active', NULL),
    (39, 'step-5-preview', 'stepfun-ai/step-5-preview', 2, 5, 'free', NULL, NULL, 'active', NULL),
    (40, 'deepseek-v4.1-flash', 'deepseek-ai/deepseek-v4.1-flash', 2, 5, 'free', NULL, NULL, 'active', NULL),
    (41, 'glm-5-3-flash', 'z-ai/glm-5-3-flash', 2, 5, 'free', NULL, NULL, 'active', NULL),
    (42, 'nemotron-parse-2.0', 'nvidia/nemotron-parse-2.0', 2, 5, 'free', NULL, NULL, 'active', NULL),
    (43, 'nemotron-3-5-lightning-30b-a3b', 'nvidia/nemotron-3.5-lightning-30b-a3b', 2, 5, 'free', NULL, NULL, 'active', NULL),
    (44, 'muse-glimmer-30b', 'meta/muse-glimmer-30b', 2, 5, 'free', NULL, NULL, 'active', NULL),
    (45, 'riva-translate-4b-instruct-v2', 'nvidia/riva-translate-4b-instruct-v2', 2, 5, 'free', NULL, NULL, 'active', NULL),
    (46, 'ising-calibration-1.5-31b', 'nvidia/ising-calibration-1.5-31b', 2, 5, 'free', NULL, NULL, 'active', NULL),
    (47, 'laguna-xs-2.1', 'poolside/laguna-xs-2.1', 2, 5, 'free', NULL, NULL, 'active', NULL),
    (48, 'diffusiongemma-26b-a4b-it', 'google/diffusiongemma-26b-a4b-it', 2, 5, 'free', NULL, NULL, 'active', NULL),
    (49, 'nemotron-3-5-content-safety', 'nvidia/nemotron-3.5-content-safety', 2, 5, 'free', NULL, NULL, 'active', NULL),
    (50, 'nemotron-3-nano-omni-30b-a3b-reasoning', 'nvidia/nemotron-3-nano-omni-30b-a3b-reasoning', 2, 5, 'free', NULL, NULL, 'active', NULL),
    (51, 'nemotron-parse', 'nvidia/nemotron-parse', 2, 5, 'free', NULL, NULL, 'active', NULL),
    (52, 'llama-3-1-nemotron-safety-guard-8b-v3', 'nvidia/llama-3_1-nemotron-safety-guard-8b-v3', 2, 5, 'free', NULL, NULL, 'active', NULL),
    (53, 'gpt-oss-20b', 'openai/gpt-oss-20b', 2, 5, 'free', NULL, NULL, 'active', NULL),
    (54, 'llama-guard-4-12b', 'meta/llama-guard-4-12b', 2, 5, 'free', NULL, NULL, 'active', NULL),
    (55, 'llama-3-1-nemoguard-8b-topic-control', 'nvidia/llama-3_1-nemoguard-8b-topic-control', 2, 5, 'free', NULL, NULL, 'active', NULL),
    (56, 'llama-3-1-nemoguard-8b-content-safety', 'nvidia/llama-3_1-nemoguard-8b-content-safety', 2, 5, 'free', NULL, NULL, 'active', NULL),
    (4, 'nemotron-super-vl', 'nemotron-3.5-super-vl-free', 3, NULL, 'free', NULL, NULL, 'active',
        'free model, no key'),
    -- OpenCode (free tier)
    (5, 'llama', 'groq/llama-3.3-70b-versatile', 4, 6, 'paid', NULL, NULL, 'active', NULL),
    (6, 'qwen-coder', 'openrouter/qwen/qwen3.8-27b:free', 5, 7, 'free', NULL, NULL, 'active', NULL),
    (7, 'deepseek-chat', 'deepseek-chat', 6, 8, 'paid', NULL, NULL, 'active', NULL),
    (8, 'mistral-small', 'mistral/mistral-small-latest', 7, 9, 'paid', NULL, NULL, 'active', NULL),
    (9, 'beam-free', 'opencode/beam-free', 3, NULL, 'free', NULL, NULL, 'active', 'OpenCode free model'),
    (10, 'big-pickle', 'opencode/big-pickle', 3, NULL, 'free', NULL, NULL, 'active', 'OpenCode free model'),
    (11, 'crouton-alpha-free', 'opencode/crouton-alpha-free', 3, NULL, 'free', NULL, NULL, 'active',
        'OpenCode free model'),
    (12, 'deepseek-v4.1-flash-free', 'opencode/deepseek-v4.1-flash-free', 3, NULL, 'free', NULL, NULL,
        'active', 'OpenCode free model'),
    (13, 'flint-40b-free', 'opencode/flint-40b-free', 3, NULL, 'free', NULL, NULL, 'active',
        'OpenCode free model'),
    (14, 'glm-5.3-flash-free', 'opencode/glm-5.3-flash-free', 3, NULL, 'free', NULL, NULL, 'active',
        'OpenCode free model'),
    (15, 'iceman-free', 'opencode/iceman-free', 3, NULL, 'free', NULL, NULL, 'active', 'OpenCode free model'),
    (16, 'inkling-2-small-free', 'opencode/inkling-2-small-free', 3, NULL, 'free', NULL, NULL, 'active',
        'OpenCode free model'),
    (17, 'mimo-v2.6-flash-free', 'opencode/mimo-v2.6-flash-free', 3, NULL, 'free', NULL, NULL, 'active',
        'OpenCode free model'),
    (18, 'nemotron-3.5-lightning-free', 'opencode/nemotron-3.5-lightning-free', 3, NULL, 'free',
        NULL, NULL, 'active', 'OpenCode free model'),
    -- Anthropic / Claude (paid, 12-15 models)
    (19, 'claude-3-5-sonnet', 'claude-3-5-sonnet-20241022', 8, 10, 'paid', 200000, NULL, 'planned', NULL),
    (20, 'claude-3-5-haiku', 'claude-3-5-haiku-20241022', 8, 10, 'paid', 200000, NULL, 'planned', NULL),
    (21, 'claude-3-opus', 'claude-3-opus-20240229', 8, 10, 'paid', 200000, NULL, 'planned', NULL),
    (22, 'claude-3-sonnet', 'claude-3-sonnet-20240229', 8, 10, 'paid', 200000, NULL, 'planned', NULL),
    (23, 'claude-3-haiku', 'claude-3-haiku-20240307', 8, 10, 'paid', 200000, NULL, 'planned', NULL),
    -- Codex (free tier, several GPT models)
    (24, 'codex-gpt-4o', 'gpt-4o', 9, 11, 'free', 128000, NULL, 'planned', NULL),
    (25, 'codex-gpt-4o-mini', 'gpt-4o-mini', 9, 11, 'free', 128000, NULL, 'planned', NULL),
    (26, 'codex-gpt-35-turbo', 'gpt-3.5-turbo', 9, 11, 'free', 16384, NULL, 'planned', NULL),
    -- Litellm + kiko hack (free tier, 4 models)
    (27, 'litellm-gpt-4', 'gpt-4', 10, 12, 'free', 8192, NULL, 'planned', NULL),
    (28, 'litellm-gpt-35', 'gpt-3.5-turbo', 10, 12, 'free', 4096, NULL, 'planned', NULL),
    (29, 'litellm-claude-instant', 'claude-instant-1', 10, 12, 'free', 100000, NULL, 'planned', NULL),
    (30, 'litellm-llama-2', 'llama-2-7b-chat', 10, 12, 'free', 4096, NULL, 'planned', NULL),
    -- Kiko proxy (free tier)
    (31, 'kiko-proxy-1', 'kiko-proxy-model-1', 11, 13, 'free', NULL, NULL, 'planned', NULL),
    (32, 'kiko-proxy-2', 'kiko-proxy-model-2', 11, 13, 'free', NULL, NULL, 'planned', NULL),
    -- Goose (unknown)
    (33, 'goose-1', 'goose-model-1', 12, NULL, 'unknown', NULL, NULL, 'planned', 'integration unknown'),
    -- Rez integrated with kiko (free tier)
    (34, 'rez-kiko-1', 'rez-kiko-model-1', 13, 14, 'free', NULL, NULL, 'planned', 'rez integrated with kiko');

INSERT OR IGNORE INTO tools (id, name, machine_id, status, notes) VALUES
    (4, 'Docker', NULL, 'planned', NULL);
