# HTML docs and diagrams

Goal: each doc page is one Markdown source plus one HTML page; each diagram is a
Mermaid source plus a committed SVG. On Windows type `py` instead of `python3`.

## Rules
- A page is a local file only: `doc/<page>.html` next to `doc/<page>.md`, committed with the change.
- Never publish or upload a page to any hosted service (the agent host's page or artifact
  publishing tools, gists, pastebins, cloud docs) unless the user explicitly asks for it in
  that conversation.
- After building, open the local file yourself: Windows `start "" doc\<page>.html`,
  Git Bash `cmd //c start "" "doc/<page>.html"`, macOS `open doc/<page>.html`,
  Linux `xdg-open doc/<page>.html`.
- A diagram shows the current code. Parts that are only planned are marked "planned".

## Files
- `doc/<page>.md` is the source. `doc/<page>.html` is the page people open.
  Today: `doc/architecture.md` -> `doc/architecture.html`.
- `doc/accessibility.html` has no source yet. Before you change it, write
  `doc/accessibility.md` from the current page.
- `doc/diagrams/<name>.mmd` is a diagram source; `doc/diagrams/<name>.svg` is the picture.
  Today: arch-overview, autodiscovery, db-schema, secret-flow.

## Change a page
1. Edit `doc/<page>.md` first.
2. Make `doc/<page>.html` say the same. There is no converter tool: write the HTML by hand.
3. Keep the HTML self-contained: inline CSS, no JavaScript, no CDN, no web fonts.
4. Show a diagram with a relative image link:
   ```html
   <div class="diagram-container">
   <img src="diagrams/<name>.svg" alt="<what the diagram shows>" style="max-width: 100%; height: auto;">
   </div>
   ```

## Change a diagram
1. Edit `doc/diagrams/<name>.mmd` in any text editor.
2. Check if you can render: `python3 tools/autodiscovery.py --no-secret-probe`.
   Look at the lines `node:` and `merman:`. Both must say `yes`.
3. Both `yes`: render the SVG.
   ```bash
   npx -y @mermaid-js/mermaid-cli -i doc/diagrams/<name>.mmd -o doc/diagrams/<name>.svg -t default -b white
   ```
   The first run downloads mermaid-cli and a Chromium browser (large, needs network).
   Ask the user before the first run.
4. Not both `yes`: do not install anything. Commit the `.mmd` and leave the old `.svg`.
   Tell the user the `.svg` is out of date.
5. Node.js is optional. It is needed only for step 3.
6. `tools.merman` in `settings.json` (copy of `settings.json.example`) may hold the
   command that runs mermaid-cli; empty = `npx -y @mermaid-js/mermaid-cli`.
   autodiscovery checks only its first word.

## View
- Open the `.html` file in your browser (double-click it in the file manager).
- Or serve the folder: `python3 -m http.server 8080 --bind 127.0.0.1 -d doc`,
  then open http://localhost:8080/architecture.html. Stop it with Ctrl+C.

## Commit
- Commit the `.md`, `.html`, `.mmd` and `.svg` of one change together
  (docs/procedures/commit.md).

## Mermaid diagram types
| Type | First line | Use |
|------|------------|-----|
| Flowchart | `flowchart TD` / `flowchart LR` | process flows |
| Sequence | `sequenceDiagram` | calls between parts |
| Class | `classDiagram` | data structures |
| State | `stateDiagram-v2` | state machines |
| ER | `erDiagram` | database schema |
