-- Initial inventory data.  Committed to git and safe to re-run: every statement is
-- INSERT OR IGNORE, so user edits in data/inventory.db are not overwritten.
-- Values of secrets are never recorded here; only key paths.

INSERT OR IGNORE INTO schema_meta (key, value) VALUES ('schema_version', '1');

INSERT OR IGNORE INTO machines (id, name, os, arch, python, user_name, role, status, notes) VALUES
    (1, 'q4os', 'Q4OS Linux (TDE)', 'x86_64', '3.13', 'petark', 'primary', 'active',
        'TDE session; /opt/trinity/bin contains dcop and tdewalletmanager'),
    (2, 'win10', 'Windows 10', 'x86_64', '3.13', 'Dani', 'secondary', 'active',
        'Windows Credential Manager is the native store');

INSERT OR IGNORE INTO services (id, name, kind, account, status, notes) VALUES
    (1, 'github', 'code hosting', 'personal', 'active', NULL),
    (2, 'gmail', 'mail', 'personal', 'active', NULL),
    (3, 'facebook', 'social', NULL, 'unknown', 'to clarify'),
    (4, 'jira', 'issue tracking', NULL, 'planned', NULL),
    (5, 'confluence', 'documentation', NULL, 'planned', NULL);

INSERT OR IGNORE INTO providers (id, name, kind, base_url, status, notes) VALUES
    (1, 'gemini', 'llm', NULL, 'active', NULL),
    (2, 'nvidia', 'llm', NULL, 'active', 'direct endpoint works; kiko-proxy returns 500'),
    (3, 'opencode', 'llm', NULL, 'active', 'free models, no key'),
    (4, 'groq', 'llm', NULL, 'active', NULL),
    (5, 'openrouter', 'llm', NULL, 'active', NULL),
    (6, 'deepseek', 'llm', NULL, 'active', NULL),
    (7, 'mistral', 'llm', NULL, 'active', NULL);

INSERT OR IGNORE INTO keys (id, path, service_id, provider_id, kind, status, notes) VALUES
    (1, 'github/personal/token', 1, NULL, 'token', 'active', NULL),
    (2, 'github/work/prj1/token', 1, NULL, 'token', 'planned', 'no value on this machine'),
    (3, 'github/work/prj2/token', 1, NULL, 'token', 'planned', 'no value on this machine'),
    (4, 'gemini/personal/api_key', NULL, 1, 'api_key', 'active', NULL),
    (5, 'nvidia/personal/api_key', NULL, 2, 'api_key', 'active', NULL),
    (6, 'groq/personal/api_key', NULL, 4, 'api_key', 'active', NULL),
    (7, 'openrouter/personal/api_key', NULL, 5, 'api_key', 'active', NULL),
    (8, 'deepseek/personal/api_key', NULL, 6, 'api_key', 'active',
        'placeholder value, not a real key yet'),
    (9, 'mistral/personal/api_key', NULL, 7, 'api_key', 'active', NULL);

INSERT OR IGNORE INTO models (id, alias, model, provider_id, key_id, status, notes) VALUES
    (1, 'gemini-flash-lite', 'gemini/gemini-3.5-flash-lite', 1, 4, 'active', NULL),
    (2, 'gemini-flash', 'gemini/gemini-3.8-flash', 1, 4, 'active', NULL),
    (3, 'nemotron-ultra', 'nvidia/nemotron-3-ultra-550b-a55b', 2, 5, 'active',
        'direct NVIDIA endpoint works'),
    (4, 'nemotron-super-vl', 'nemotron-3.5-super-vl-free', 3, NULL, 'active',
        'free model, no key'),
    (5, 'llama', 'groq/llama-3.3-70b-versatile', 4, 6, 'active', NULL),
    (6, 'qwen-coder', 'openrouter/qwen/qwen3.8-27b:free', 5, 7, 'active', NULL),
    (7, 'deepseek-chat', 'deepseek-chat', 6, 8, 'active', NULL),
    (8, 'mistral-small', 'mistral/mistral-small-latest', 7, 9, 'active', NULL);

INSERT OR IGNORE INTO tools (id, name, machine_id, status, notes) VALUES
    (1, 'Python', 1, 'active', NULL),
    (2, 'Python', 2, 'active', NULL),
    (3, 'Git', 1, 'active', NULL),
    (4, 'Docker', NULL, 'planned', NULL),
    (5, 'Windows 10 SDK', 2, 'planned', NULL),
    (6, 'MSVC + linker', 2, 'planned', NULL);

INSERT OR IGNORE INTO settings (key, value) VALUES
    ('active_model', 'nemotron-ultra'),
    ('default_backend', 'auto'),
    ('export_file', '~/SECRETS');
