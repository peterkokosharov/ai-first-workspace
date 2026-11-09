# Project Architecture — Portable Development Workspace

Self-contained, portable folder for AI-assisted software development.

## 1. Repository Layout

```
./
├── AGENTS.md              # project rules (single source of truth)
├── README.md              # entry point, how to continue on another machine
├── doc/
│   ├── architecture.html  # this file — architecture & UML diagrams
│   └── diagrams/
│       ├── arch-overview.mmd   # Mermaid source
│       ├── arch-overview.svg   # rendered SVG
│       ├── secret-flow.mmd
│       ├── secret-flow.svg
│       ├── db-schema.mmd
│       ├── db-schema.svg
│       ├── autodiscovery.mmd
│       └── autodiscovery.svg
├── lib/
│   ├── README.md              # vendored kikolib provenance & license
│   └── kikolib/               # vendored stdlib keystore + factory (MIT)
│       ├── __init__.py
│       ├── dotenv.py
│       ├── factory.py
│       ├── http_client.py
│       ├── keystore.py
│       ├── native_utils.py
│       ├── posix_utils.py
│       ├── retry.py
│       ├── server.py
│       ├── sse.py
│       ├── tokens.py
│       └── yaml_lite.py
├── data/
│   ├── schema.sql         # committed SQLite schema
│   ├── seed.sql           # committed initial inventory data
│   └── inventory.db       # local only, gitignored
├── docs/
│   └── procedures/        # step-by-step procedures (step-review, commit, HTML docs, ...)
├── tools/
│   ├── __init__.py
│   ├── secret.py          # portable secret tool over native stores
│   ├── inventory.py       # SQLite inventory manager
│   ├── autodiscovery.py   # machine discovery (OS, RAM, git, bash, db)
│   ├── ping.py            # model ping via OpenCode
│   ├── ping_direct.py     # direct HTTP ping to providers (KWallet keys)
│   ├── setup_providers.py # configure OpenCode providers from KWallet
│   └── tests/             # functional tests (57 tests, all pass)
│       ├── __init__.py
│       ├── secret.py
│       ├── inventory.py
│       ├── autodiscovery.py
│       ├── test_secret.py
│       ├── test_inventory.py
│       └── test_autodiscovery.py
├── out/                   # reports and test output, not versioned
├── .tmp/                  # temporary files, not versioned
└── .gitignore
```

## 2. Architecture Diagram — Component Interaction

```mermaid
flowchart TB
    User((User / Agent)) -->|Bulgarian chat| AGENTS[AGENTS.md rules]
    User -->|commands| Secret[tools/secret.py]
    User -->|inventory| Inv[tools/inventory.py]
    User -->|discovery| Auto[tools/autodiscovery.py]
    User -->|ping models| Ping[tools/ping.py]
    User -->|direct HTTP| PingD[tools/ping_direct.py]
    
    Secret -->|native store| KWallet[(KWallet / DCOP)]
    Secret -->|native store| WCM[(Windows Credential Manager)]
    Secret -->|native store| KC[(macOS Keychain)]
    Secret -->|native store| ST[secret-tool]
    Secret -->|export file| SECRETS[(~/SECRETS temp)]
    
    Inv -->|SQLite| DB[(data/inventory.db)]
    Auto -->|checks| DB
    Auto -->|checks| OS[OS / RAM / Python / git / bash]
    
    Ping -->|OpenCode| OC[OpenCode CLI]
    PingD -->|HTTP API| Providers[(Providers: Gemini, NVIDIA, Groq, Mistral, ...)]
    
    Lib[lib/kikolib] -->|factory| Secret
    Lib[lib/kikolib] -->|keystore| Secret
    Lib -->|factory| Inv
    
    style User fill:#e1f5fe,stroke:#01579b
    style DB fill:#fff3e0,stroke:#e65100
    style SECRETS fill:#ffebee,stroke:#c62828
```

## 3. Secret Tool Flow

```mermaid
sequenceDiagram
    participant U as User/Agent
    participant S as secret.py
    participant K as kikolib.factory
    participant N as Native Store
    participant DB as inventory.db

    U->>S: set provider/scope/kind (stdin value)
    S->>K: choose backend (auto/file/wcm/keychain/secret-tool/kwallet/dcop)
    K-->>S: selected backend
    alt backend == file
        S->>SECRETS: write KEY_PATH | value (atomic, mode 600)
    else backend == dcop
        S->>N: dcop kded tdewalletd open kdewallet
        N-->>S: handle
        S->>N: writePassword(handle, Passwords, key, value)
        N-->>S: 0 (success)
        S->>N: close(handle)
    end
    S-->>U: OK / error code
    S->>DB: optional: record key path in inventory
```

## 4. Inventory Database Schema

```mermaid
erDiagram
    machines ||--o{ tools : "hosts"
    services ||--o{ keys : "owns"
    providers ||--o{ keys : "owns"
    providers ||--o{ models : "provides"
    keys ||--o{ models : "secures"
    
    machines {
        int id PK
        text name
        text os
        text python
        text status
    }
    
    services {
        int id PK
        text name
        text kind
        text account
    }
    
    providers {
        int id PK
        text name
        int free_tier
        text status
    }
    
    keys {
        int id PK
        text path
        int service_id FK
        int provider_id FK
        text kind
        text status
    }
    
    models {
        int id PK
        text alias
        text model_id
        int provider_id FK
        int key_id FK
        text tier
        text status
    }
    
    tools {
        int id PK
        text name
        int machine_id FK
        text status
    }
    
    settings {
        text key PK
        text value
    }
```

## 5. Auto-Discovery Procedure

```mermaid
flowchart TD
    Start([New machine / missing secret.py or inventory.db])
    --> AD[python3 tools/autodiscovery.py]
    AD --> CheckOS{OS, RAM, processor, Python version}
    CheckOS --> CheckGit{git installed?}
    CheckGit --> CheckBash{bash / Git Bash on Windows?}
    CheckBash --> MinimumMet{Minimum met?}
    MinimumMet -->|No| Install[Install git / bash]
    MinimumMet -->|Yes| CheckDB{data/inventory.db exists?}
    CheckDB -->|No| Init[python3 tools/inventory.py init]
    CheckDB -->|Yes| HasTables{has tables?}
    HasTables -->|No| Init
    HasTables -->|Yes| Ready[Ready to work]
    Install --> CheckBash
    Init --> Ready
    
    style Start fill:#e1f5fe
    style Ready fill:#d4edda
    style Install fill:#fff3cd
```

## 6. OpenCode Desktop — Visual Concept

OpenCode is a terminal TUI (Terminal User Interface) application — the entire interface runs in a single terminal window, without split GUI panes. Conceptual layout:

```
konsole — user@host: ~/ai-first-workspace
─────────────────────────────────────────────────────────────────────
 OpenCode v2 — Portable Workspace (Q4OS/TDE)
─────────────────────────────────────────────────────────────────────

 > zdr. suzdadem agents.md

 █  Разбирайки задачата, създавам AGENTS.md с правила за проекта...
 █  Правила: език, записи, самодостатъчност, технически изисквания,
 █  работни навици, без инициатива без разрешение.
 █
 █  Git операции: lokalen commit/push без дискусия.
 █  git push remote изисква изрично „да“.
 █
 █  Създавам AGENTS.md...
 █  [done] AGENTS.md written (126 lines)

 ─────────────────────────────────────────────────────────────────────
 > python3 tools/autodiscovery.py

 █  === Portable workspace auto-discovery ===
 █  OS: Linux 6.12 Q4OS (TDE)
 █  Processor: x86_64 | RAM: 7767 MB
 █  Python: 3.13.5 | git: yes | bash: yes
 █  Minimum met: git bash + Python stdlib are present.
 █  tools/secret.py: present
 █  tools/inventory.py: present
 █  data/inventory.db: exists
 █
 █  Notes: GitHub token and email are OPTIONAL.
 █  auto never falls back to plaintext.

 ─────────────────────────────────────────────────────────────────────
 > python3 -m unittest discover -s tools/tests -t . -v

 █  Ran 57 tests in 6.7s
 █  OK (skipped=1)
 █  ✓ All functional tests pass

 ─────────────────────────────────────────────────────────────────────
 █  Waiting for your command...
```

**Notes:** The entire interface runs in one terminal window (TUI). Chat is in Bulgarian Cyrillic. Project records are in English. Secret values are never printed — `list` and `probe` show only key paths. The KWallet/DCOP wallet on Q4OS must be opened once manually before `secret.py` can use it.

## 7. What Is Missing / Recommendations

- **OpenCode provider configuration:** Gemini, NVIDIA, DeepSeek, Mistral providers are not yet configured in OpenCode. Use `tools/setup_providers.py` to add them with keys from KWallet.
- **Live DCOP test:** Run `SECRET_LIVE_TESTS=1 python3 -m unittest discover -s tools/tests -t . -v` after opening the KWallet.
- **External audit:** before a release, follow `docs/procedures/release-audit.md`; reports go to `out/`.
- **Git remote:** No `origin` configured yet. Add remote and push when ready.
