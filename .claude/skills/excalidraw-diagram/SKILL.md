---
name: excalidraw-diagram
description: Turn a one-line request into a hand-drawn Excalidraw diagram (boxes, labelled arrows, dark canvas) saved as .excalidraw and/or Obsidian .excalidraw.md. Use when the user asks to diagram, map, sketch, or visualise a system, workflow, architecture, framework, or concept ("diagram the Four Cs of my second brain", "draw how this n8n flow works", "sketch the agent loop").
---

# Excalidraw diagram

One phrase in, a diagram out. You write a small JSON spec, `scripts/draw.py` does the layout, colours, arrow binding and file format. Do not hand-write Excalidraw JSON.

## Workflow

1. **Work out the content.** If the request is about the user's own system (a vault, a repo, a workflow), read the relevant files first so boxes contain real names, paths and tools, not generic filler. Keep it to 3 to 9 nodes.
2. **Write the spec** to a temp file (scratchpad if you have one). Format below.
3. **Run it:**
   ```bash
   python3 .claude/skills/excalidraw-diagram/scripts/draw.py spec.json -o <output dir> --svg
   ```
   Default output dir: `Brain/Diagrams/` if it exists, else `diagrams/` in the project root. Use `--format obsidian` when the target is an Obsidian vault, `--format excalidraw` for excalidraw.com, `both` (default) when unsure.
4. **Check it.** Open the SVG preview (render to PNG with Playwright/Chromium if you need to see it) and fix overlaps or cramped labels by adjusting rows/cols or `gapX`/`gapY`, then re-run.
5. **Report** the saved path in one line and how to open it (Obsidian: just click it with the Excalidraw plugin installed; otherwise drag the `.excalidraw` file onto excalidraw.com). Delete the SVG unless the user wants it.

## Spec format

```json
{
  "name": "four-cs-second-brain",
  "title": "The Four Cs of my second brain",
  "subtitle": "optional smaller line under the title",
  "theme": "dark",
  "style": "sketch",
  "font": "hand",
  "nodes": [
    {"id": "core", "label": "Claude Code", "color": "purple", "row": 1, "col": 1,
     "body": ["Reads memory", "Picks a skill", "Drafts, never sends"]}
  ],
  "edges": [
    {"from": "context", "to": "core", "label": "loads"}
  ]
}
```

Nodes: `id`, `label` required. `body` is a list of short lines (keep each under ~28 chars, 1 to 4 lines). `row`/`col` place the node on a grid (0-based, half steps like `0.5` are fine for offsets). Omit both and nodes run left to right on row 0. `stroke: "dashed"` for optional/external things.

Edges: `from`, `to`, optional `label` (1 to 2 words reads best), `style: "dashed"`, `both: true` for two-way, `color` (palette name or hex).

Top-level options: `theme` `dark` (default) | `light`. `style` `sketch` (default) | `clean` | `rough`. `font` `hand` (default, Virgil) | `normal` | `mono`. Tuning: `gapX` (140), `gapY` (110), `minNodeWidth` (200), `nodeTitleSize` (20), `nodeBodySize` (14), `edgeLabelSize` (14), `titleSize` (36). Title is optional; skip it when the diagram is going on a slide that already has one.

Colours: `blue`, `purple`, `green`, `orange`, `red`, `teal`, `yellow`, `gray`.

## Layout patterns

Pick the shape that matches the idea, then assign rows/cols:

- **Hub and spoke** (the screenshot style, one core thing with inputs/outputs on each side): core at (1,1), others at (0,1), (1,0), (1,2), (2,1). Make the hub `purple`, the trigger/scheduler `green`, everything else `blue`.
- **Pipeline** (A then B then C): everything on row 0, cols 0..n. Long pipelines (6+) wrap onto row 1.
- **Layers** (frontend / API / DB): one row per layer, nodes spread across cols.
- **Fan out / fan in** (router, parallel agents): source at (1,0), workers at (0,1), (1,1), (2,1), sink at (1,2).

## Style rules

- Colour carries meaning: one accent for the centre of gravity, one for time/trigger, one neutral for the rest. Don't rainbow it.
- Edge labels are verbs (`loads`, `uses`, `triggers`, `writes to`), not nouns.
- Body text is concrete: file names, tool names, real behaviour. "tools/query.py" beats "data layer".
- No edges crossing through boxes. If one would, move a node or add a row.

See `examples/four-cs.json` for a full working spec.
