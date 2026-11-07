# HTML Documentation Generation (Mermaid Diagrams)

This document describes how to generate and maintain self-contained HTML
documentation with Mermaid.js diagrams, based on `in/HOWTO_HTML_DOCS.md`.

## Overview

Documentation is generated as a single self-contained HTML file that includes:

- **Mermaid.js diagrams** rendered client-side (no build step needed)
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
├── HOWTO_HTML_DOCS.md         # How-to guide (source: in/HOWTO_HTML_DOCS.md)
├── diagrams/                  # Optional: standalone .mmd files
│   ├── monorepo-structure.mmd
│   ├── request-flow.mmd
│   ├── health-probe.mmd
│   └── data-model.mmd
└── tests-results/             # Test result artifacts (HTML/XML)
```

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
| Flowchart | `flowchart TD` / `flowchart LR` | Process flows, sequences |
| Sequence | `sequenceDiagram` | API calls, interactions |
| Class | `classDiagram` | Data structures, models |
| State | `stateDiagram-v2` | State machines (health, cooldown) |
| Git | `gitGraph` | Branching workflows |
| Gantt | `gantt` | Timelines, releases |
| ER | `erDiagram` | Database schema |
| Journey | `journey` | User journeys |

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

## Viewing the HTML

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

## Recommended Workflow

```bash
# 1. Edit diagrams in HTML
vim docs/architecture.html

# 2. Verify in browser
xdg-open docs/architecture.html

# 3. Optionally export standalone .mmd files
cp "extracted diagram" docs/diagrams/new-diagram.mmd

# 4. Commit
git add docs/architecture.html docs/diagrams/*.mmd
git commit -m "docs: add X diagram"
```

## Adding New Sections (Checklist)

- [ ] Add `<section id="unique-id">` in HTML
- [ ] Add entry to Table of Contents (`.toc ul`)
- [ ] Include diagram(s) in `.diagram-container`
- [ ] Each `.mermaid` div has unique `id`
- [ ] Test in browser (light + dark mode)
- [ ] Update this HOWTO if new patterns emerge

## Source

This procedure is based on `in/HOWTO_HTML_DOCS.md`.
