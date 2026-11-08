# How to Generate HTML Documentation with Mermaid Diagrams (kiko)

## Overview

The architecture documentation for kiko is generated as a single self-contained HTML file (`docs/architecture.html`) that includes:

- **Mermaid.js diagrams** rendered in-browser (no build step needed)
- **Fullscreen modal** for diagram viewing with zoom/pan
- **Responsive design** — works on mobile/tablet/desktop
- **All diagrams embedded** in the HTML — single file to share
- **Dark mode support** — follows system preference

## Prerequisites

- Mermaid.js loaded from CDN (`https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js`)
- Modern browser with ES6 support
- No Node.js, Python, or build tools required for viewing

## File Structure

```
docs/
├── architecture.html          # Main documentation (self-contained HTML)
├── HOWTO_HTML_DOCS.md         # This file
├── KIKO_DOT_DIR.md            # ~/.kiko/ documentation
├── QUALITY_REPORT.md          # Code quality report
├── TEST_REPORT_*.md           # Test reports
├── tests-results/             # Test result artifacts (HTML/XML)
└── diagrams/                  # Optional: standalone .mmd files
    ├── monorepo-structure.mmd
    ├── request-flow.mmd
    ├── health-probe.mmd
    └── data-model.mmd
```

---

## Creating New Diagrams

### 1. Add Mermaid Code Block in HTML

Edit `docs/architecture.html` and add a new diagram section:

```html
<section id="your-section">
    <h2>Your Section Title</h2>
    <div class="diagram-container">
        <div class="mermaid" id="your-diagram-id">
flowchart TD
    A[Start] --> B[Process]
    B --> C[End]
        </div>
    </div>
</section>
```

### 2. Mermaid Diagram Types Supported

| Type | Syntax | Use Case |
|------|--------|----------|
| **Flowchart** | `flowchart TD` / `flowchart LR` | Process flows, sequences |
| **Sequence** | `sequenceDiagram` | API calls, interactions |
| **Class** | `classDiagram` | Data structures, models |
| **State** | `stateDiagram-v2` | State machines (health, cooldown) |
| **Git** | `gitGraph` | Branching workflows |
| **Gantt** | `gantt` | Timelines, releases |
| **ER** | `erDiagram` | Database schema |
| **Journey** | `journey` | User journeys |

### 3. Diagram Styling (CSS in HTML)

```css
.diagram-container {
    background: var(--card-bg, #fff);
    border: 1px solid var(--border, #e0e0e0);
    border-radius: 8px;
    padding: 1rem;
    margin: 1rem 0;
    overflow: auto;
}

.mermaid {
    display: flex;
    justify-content: center;
}

@media (prefers-color-scheme: dark) {
    .diagram-container {
        background: #1e1e1e;
        border-color: #444;
    }
}
```

### 4. Fullscreen Modal (built-in)

Diagrams are automatically included in the fullscreen modal via JavaScript:

```javascript
const diagrams = document.querySelectorAll('.mermaid[id]');
// Each diagram with an ID gets added to modal
```

**Requirement**: Each `.mermaid` div **must have a unique `id` attribute**.

---

## kiko-Specific Diagram Examples

### Monorepo Structure (Current)
```mermaid
flowchart TB
    subgraph Root["kiko (monorepo)"]
        pyproject["pyproject.toml"]
        docs["docs/"]
        packages["packages/"]
    end

    subgraph Packages["packages/"]
        core["core/kiko_core/"]
        kikolib["kikolib/kikolib/"]
        spy["spy/kiko_spy/"]
        web["web/kiko_web/"]
        proxy["proxy/kiko_proxy/"]
        tqt3["tqt3/"]
    end

    pyproject --> packages
    docs --> packages
    packages --> core
    packages --> kikolib
    packages --> spy
    packages --> web
    packages --> proxy
    packages --> tqt3
```

### Future: kiko-life (Separate Project)
```mermaid
flowchart TB
    subgraph Current["kiko monorepo (embedded)"]
        core["kiko-core"]
        kikolib["kikolib"]
        spy["kiko-spy"]
        web["kiko-web"]
        proxy["kiko-proxy"]
        tqt3["kiko-tqt3"]
    end

    subgraph Future["kiko-life (separate repo)"]
        life_core["kiko-life-core"]
        life_proxy["kiko-life-proxy"]
        life_ui["kiko-life-ui"]
    end

    Current -.->|"split/extract"| Future
    
    subgraph Shared["shared (always)"]
        kikolib_shared["kikolib (stdlib kernel)"]
    end

    Current --> kikolib_shared
    Future --> kikolib_shared
```

> **Note**: `kiko-life` е отделен проект (LiteLLM-compatible proxy). Тук базираме на `kiko-lite` (embedded версия). `kiko-life` ще се "chopne" (изреже) като отделен репо по-късно.

### Request Flow (kiko-proxy → providers)
```mermaid
sequenceDiagram
    participant Client
    participant Proxy as kiko-proxy
    participant Resolver
    participant Health as HealthProber
    participant Provider

    Client->>Proxy: POST /v1/chat/completions
    Proxy->>Resolver: resolve(model)
    Resolver-->>Proxy: [(provider, model_id), ...]
    Proxy->>Health: check cooldown
    Health-->>Proxy: live targets
    loop failover
        Proxy->>Provider: request
        alt success
            Provider-->>Proxy: response
            Proxy-->>Client: SSE stream
        else failover error
            Proxy->>Health: cool model
        end
    end
```

### Health Probe State Machine
```mermaid
stateDiagram-v2
    [*] --> Unknown
    Unknown --> Probing: health_check_interval
    Probing --> OK: success
    Probing --> Error: failure
    Probing --> Unknown: no verdict
    OK --> Probing: interval elapsed
    Error --> Probing: backoff expired
    Error --> OK: success
    Unknown --> OK: live success (passive)
```

### Database Schema (ER)
```mermaid
erDiagram
    MODELS ||--o{ BILLING : "generates"
    MODELS ||--o{ RESPONSES : "logs"
    MODELS }|--|| MODEL_CLASSES : "belongs to"
    MODELS ||--o{ ALIASES : "targeted by"
    SETTINGS ||--o{ MODELS : "configures"
    
    MODELS {
        text alias PK
        text provider
        text api_key_env
        text api_base
        text model_class
        int priority
        bool enabled
        text status
        real price_in
        real price_out
    }
    BILLING {
        int id PK
        text model
        int tokens_in
        int tokens_out
        real cost_usd
        timestamp ts
        text route
        int attempts
        int latency_ms
        text error
    }
```

---

## Updating Documentation

1. **Edit source Markdown** (if you maintain `.md` source): `docs/architecture-source.md`
2. **Update diagrams** in `docs/architecture.html`
3. **Open in browser** to verify: `xdg-open docs/architecture.html`
4. **Commit both files**

### Recommended Workflow

```bash
# 1. Edit diagrams in HTML (or standalone .mmd files)
vim docs/architecture.html

# 2. Verify in browser
xdg-open docs/architecture.html

# 3. Optionally export standalone .mmd files to diagrams/
cp "extracted diagram" docs/diagrams/new-diagram.mmd

# 4. Commit
git add docs/architecture.html docs/diagrams/*.mmd
git commit -m "docs: add X diagram"
```

---

## Viewing

```bash
# Linux
xdg-open docs/architecture.html

# macOS
open docs/architecture.html

# Windows
start docs/architecture.html

# Or serve locally (for CSP-restricted environments)
python3 -m http.server 8080 -d docs
# Then open http://localhost:8080/architecture.html
```

---

## Features

| Feature | Implementation |
|---------|----------------|
| **No build step** | Mermaid renders client-side from CDN |
| **Fullscreen** | Click "⛶ Fullscreen All" button |
| **Zoom/Pan** | Mouse wheel zoom, drag to pan in modal |
| **Dark mode** | Auto-detects `prefers-color-scheme` |
| **Printable** | CSS `@media print` styles included |
| **Responsive** | Works on mobile/tablet/desktop |
| **Keyboard nav** | `Esc` closes modal, arrows navigate |

---

## Adding New Sections (Checklist)

- [ ] Add `<section id="unique-id">` in HTML
- [ ] Add entry to Table of Contents (`.toc ul`)
- [ ] Include diagram(s) in `.diagram-container`
- [ ] Each `.mermaid` div has unique `id`
- [ ] Test in browser (light + dark mode)
- [ ] Update this HOWTO if new patterns emerge

---

## Reference Files

- **Template**: `docs/architecture.html` (edit this)
- **Source**: `docs/architecture-source.md` (optional, for content)
- **Standalone diagrams**: `docs/diagrams/*.mmd` (for embedding elsewhere)
- **Test results**: `docs/tests-results/*.html` (coverage reports)