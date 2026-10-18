#!/usr/bin/env python3
"""Turn a small JSON diagram spec into an Excalidraw drawing.

Usage:
    python3 draw.py spec.json [-o out/dir] [--format excalidraw|obsidian|both] [--svg]

Writes <name>.excalidraw (plain Excalidraw JSON), <name>.excalidraw.md
(Obsidian Excalidraw plugin format), or both. --svg also writes a flat
preview. Standard library only.
"""

import argparse
import json
import math
import random
import re
import sys
import time
from pathlib import Path

# Dark-canvas palette. Each colour is (fill, stroke, title text, body text).
PALETTE = {
    "blue":   ("#12304d", "#4a9fe0", "#e6f1ff", "#b9d4f0"),
    "purple": ("#2a2350", "#9b87f5", "#efeaff", "#cdc3f7"),
    "green":  ("#123d1c", "#4cc062", "#e6ffea", "#b8e6c1"),
    "orange": ("#47290f", "#f0a04b", "#fff1e0", "#f2cfa6"),
    "red":    ("#4a1717", "#f06a6a", "#ffe6e6", "#f2b8b8"),
    "teal":   ("#0f3a3a", "#3fc1c1", "#e0ffff", "#b0e6e6"),
    "yellow": ("#423a0e", "#e8c94a", "#fffbe0", "#efe2a8"),
    "gray":   ("#24272e", "#8b949e", "#f0f3f6", "#c9d1d9"),
}
THEMES = {
    "dark":  {"bg": "#0d1117", "edge": "#6aa6e8", "label": "#c9d1d9", "title": "#e6edf3"},
    "light": {"bg": "#ffffff", "edge": "#1e66c4", "label": "#343a40", "title": "#1e1e1e"},
}
# Light theme reuses the hue but with pale fills and dark text.
LIGHT_PALETTE = {
    "blue":   ("#dbeafe", "#1e66c4", "#0b2545", "#1f3b63"),
    "purple": ("#ede9fe", "#6d4fd1", "#2a1a66", "#45348f"),
    "green":  ("#dcfce7", "#2f9e44", "#0b3d17", "#1f5c2b"),
    "orange": ("#ffedd5", "#e8590c", "#5a2306", "#7a3a12"),
    "red":    ("#fee2e2", "#e03131", "#5c0d0d", "#7a1d1d"),
    "teal":   ("#ccfbf1", "#0c8599", "#063a40", "#155e66"),
    "yellow": ("#fef9c3", "#f08c00", "#4d3800", "#6b5000"),
    "gray":   ("#f1f3f5", "#495057", "#1e1e1e", "#343a40"),
}
FONTS = {"hand": 1, "normal": 2, "mono": 3}
# Rough average glyph width as a fraction of font size, per font family.
CHAR_W = {1: 0.58, 2: 0.55, 3: 0.6}
LINE_H = 1.25

NOW = int(time.time() * 1000)
_rng = random.Random(42)


def _id():
    return "".join(_rng.choice("abcdefghijklmnopqrstuvwxyz0123456789") for _ in range(16))


def _base(kind, x, y, w, h, **kw):
    el = {
        "id": kw.pop("id", None) or _id(),
        "type": kind,
        "x": round(x, 2), "y": round(y, 2),
        "width": round(w, 2), "height": round(h, 2),
        "angle": 0,
        "strokeColor": "#1e1e1e",
        "backgroundColor": "transparent",
        "fillStyle": "solid",
        "strokeWidth": 2,
        "strokeStyle": "solid",
        "roughness": 1,
        "opacity": 100,
        "groupIds": [],
        "frameId": None,
        "roundness": None,
        "seed": _rng.randint(1, 2**31 - 1),
        "version": 1,
        "versionNonce": _rng.randint(1, 2**31 - 1),
        "isDeleted": False,
        "boundElements": [],
        "updated": NOW,
        "link": None,
        "locked": False,
    }
    el.update(kw)
    return el


def text_size(text, size, family):
    lines = text.split("\n")
    w = max(len(l) for l in lines) * size * CHAR_W[family]
    h = len(lines) * size * LINE_H
    return w, h


def make_text(text, x, y, size, family, color, align="left", **kw):
    w, h = text_size(text, size, family)
    if align == "center":
        x -= w / 2
    return _base(
        "text", x, y, w, h,
        strokeColor=color,
        text=text, originalText=text,
        fontSize=size, fontFamily=family,
        textAlign=align, verticalAlign="top",
        containerId=None, autoResize=True, lineHeight=LINE_H,
        **kw,
    )


def load_spec(path):
    spec = json.loads(Path(path).read_text())
    if not spec.get("nodes"):
        sys.exit("spec needs a non-empty 'nodes' list")
    ids = {n["id"] for n in spec["nodes"]}
    for e in spec.get("edges", []):
        for end in ("from", "to"):
            if e[end] not in ids:
                sys.exit(f"edge references unknown node '{e[end]}'")
    return spec


def layout(spec):
    """Size every node, then place nodes on a row/col grid.

    Nodes without row/col are laid out left to right on row 0.
    Column widths and row heights grow to fit their largest box.
    """
    family = FONTS.get(spec.get("font", "hand"), 1)
    title_size = spec.get("nodeTitleSize", 20)
    body_size = spec.get("nodeBodySize", 14)
    pad_x, pad_y = 24, 18
    min_w = spec.get("minNodeWidth", 200)

    auto_col = 0
    for n in spec["nodes"]:
        body = n.get("body", [])
        if isinstance(body, str):
            body = [body]
        n["_body"] = "\n".join(body)
        tw, th = text_size(n["label"], title_size, family)
        bw, bh = text_size(n["_body"], body_size, family) if body else (0, 0)
        n["_w"] = max(min_w, tw, bw) + pad_x * 2
        n["_h"] = pad_y * 2 + th + (bh + 10 if body else 0)
        if "row" not in n and "col" not in n:
            n["row"], n["col"] = 0, auto_col
            auto_col += 1
        n.setdefault("row", 0)
        n.setdefault("col", 0)

    gap_x = spec.get("gapX", 140)
    gap_y = spec.get("gapY", 110)
    cols = sorted({n["col"] for n in spec["nodes"]})
    rows = sorted({n["row"] for n in spec["nodes"]})
    col_w = {c: max(n["_w"] for n in spec["nodes"] if n["col"] == c) for c in cols}
    row_h = {r: max(n["_h"] for n in spec["nodes"] if n["row"] == r) for r in rows}

    # Half-step columns/rows (e.g. col 0.5) still work: positions interpolate.
    def axis(keys, size, gap):
        pos, cur = {}, 0
        for k in keys:
            pos[k] = cur + size[k] / 2
            cur += size[k] + gap
        return pos

    cx = axis(cols, col_w, gap_x)
    cy = axis(rows, row_h, gap_y)
    top = 0
    if spec.get("title"):
        top = spec.get("titleSize", 36) * LINE_H + (spec.get("subtitleSize", 18) * LINE_H if spec.get("subtitle") else 0) + 50
    for n in spec["nodes"]:
        n["_x"] = cx[n["col"]] - n["_w"] / 2
        n["_y"] = top + cy[n["row"]] - n["_h"] / 2
    return family, title_size, body_size, pad_y


def edge_point(n, tx, ty, gap=8):
    """Where the line from n's centre toward (tx, ty) leaves n's box, plus a gap."""
    cx, cy = n["_x"] + n["_w"] / 2, n["_y"] + n["_h"] / 2
    dx, dy = tx - cx, ty - cy
    if dx == 0 and dy == 0:
        return cx, cy
    hw, hh = n["_w"] / 2 + gap, n["_h"] / 2 + gap
    s = min(hw / abs(dx) if dx else math.inf, hh / abs(dy) if dy else math.inf)
    return cx + dx * s, cy + dy * s


def build(spec):
    theme_name = spec.get("theme", "dark")
    theme = THEMES[theme_name]
    palette = PALETTE if theme_name == "dark" else LIGHT_PALETTE
    roughness = {"clean": 0, "sketch": 1, "rough": 2}.get(spec.get("style", "sketch"), 1)
    family, title_size, body_size, pad_y = layout(spec)
    nodes = {n["id"]: n for n in spec["nodes"]}
    els = []

    if spec.get("title"):
        size = spec.get("titleSize", 36)
        els.append(make_text(spec["title"], 0, 0, size, family, theme["title"], roughness=roughness))
        if spec.get("subtitle"):
            els.append(make_text(spec["subtitle"], 0, size * LINE_H + 6,
                                 spec.get("subtitleSize", 18), family, theme["label"],
                                 roughness=roughness))

    for n in spec["nodes"]:
        fill, stroke, tcol, bcol = palette.get(n.get("color", "blue"), palette["blue"])
        group = _id()
        rect = _base(
            "rectangle", n["_x"], n["_y"], n["_w"], n["_h"],
            id=f"node-{n['id']}",
            strokeColor=stroke, backgroundColor=fill,
            roundness={"type": 3}, roughness=roughness, groupIds=[group],
            strokeStyle=n.get("stroke", "solid"),
        )
        n["_el"] = rect
        els.append(rect)
        mid = n["_x"] + n["_w"] / 2
        y = n["_y"] + pad_y
        title = make_text(n["label"], mid, y, title_size, family, tcol, "center",
                          groupIds=[group], roughness=roughness)
        els.append(title)
        if n["_body"]:
            els.append(make_text(n["_body"], mid, y + title["height"] + 10, body_size,
                                 family, bcol, "center", groupIds=[group], roughness=roughness))

    for e in spec.get("edges", []):
        a, b = nodes[e["from"]], nodes[e["to"]]
        acx, acy = a["_x"] + a["_w"] / 2, a["_y"] + a["_h"] / 2
        bcx, bcy = b["_x"] + b["_w"] / 2, b["_y"] + b["_h"] / 2
        # Snap near-aligned boxes so arrows come out straight.
        if abs(acx - bcx) < 30:
            bcx = acx
        if abs(acy - bcy) < 30:
            bcy = acy
        sx, sy = edge_point(a, bcx, bcy)
        ex, ey = edge_point(b, acx, acy)
        color = e.get("color") or theme["edge"]
        if e.get("color") in palette:
            color = palette[e["color"]][1]
        arrow = _base(
            "arrow", sx, sy, abs(ex - sx), abs(ey - sy),
            strokeColor=color, roughness=roughness,
            strokeStyle=e.get("style", "solid"),
            roundness={"type": 2},
            points=[[0, 0], [round(ex - sx, 2), round(ey - sy, 2)]],
            lastCommittedPoint=None,
            startBinding={"elementId": a["_el"]["id"], "focus": 0, "gap": 8},
            endBinding={"elementId": b["_el"]["id"], "focus": 0, "gap": 8},
            startArrowhead="arrow" if e.get("both") else None,
            endArrowhead="arrow",
            elbowed=False,
        )
        a["_el"]["boundElements"].append({"id": arrow["id"], "type": "arrow"})
        b["_el"]["boundElements"].append({"id": arrow["id"], "type": "arrow"})
        els.append(arrow)
        if e.get("label"):
            lsize = spec.get("edgeLabelSize", 14)
            lw, lh = text_size(e["label"], lsize, family)
            mx, my = (sx + ex) / 2, (sy + ey) / 2
            dx, dy = ex - sx, ey - sy
            if abs(dx) < 1:
                # Vertical: label sits to the right.
                lx, ly = mx + 12, my - lh / 2
            elif abs(dy) < 1:
                # Horizontal: label sits above.
                lx, ly = mx - lw / 2, my - lh - 8
            else:
                # Diagonal: push the label off the line along its upward normal,
                # far enough that the label box clears the line.
                ln = math.hypot(dx, dy)
                nx, ny = -dy / ln, dx / ln
                if ny > 0:
                    nx, ny = -nx, -ny
                d = (abs(nx) * lw + abs(ny) * lh) / 2 + 8
                lx, ly = mx + nx * d - lw / 2, my + ny * d - lh / 2
            els.append(make_text(e["label"], lx, ly, lsize, family, theme["label"],
                                 roughness=roughness))

    return {
        "type": "excalidraw",
        "version": 2,
        "source": "https://excalidraw.com",
        "elements": els,
        "appState": {"viewBackgroundColor": theme["bg"], "gridSize": None,
                     "currentItemFontFamily": family, "theme": "light"},
        "files": {},
    }


def to_obsidian(doc):
    texts = "\n\n".join(f"{el['text']} ^{el['id']}" for el in doc["elements"] if el["type"] == "text")
    return (
        "---\n\nexcalidraw-plugin: parsed\ntags: [excalidraw]\n\n---\n"
        "==⚠  Switch to EXCALIDRAW VIEW in the MORE OPTIONS menu of this document. ⚠==\n\n\n"
        f"# Excalidraw Data\n## Text Elements\n{texts}\n\n"
        "%%\n## Drawing\n```json\n" + json.dumps(doc, indent=2) + "\n```\n%%"
    )


def to_svg(doc):
    """Flat (non-sketchy) preview so you can eyeball layout without Excalidraw."""
    els = doc["elements"]
    xs, ys = [], []
    for el in els:
        xs += [el["x"], el["x"] + el["width"]]
        ys += [el["y"], el["y"] + el["height"]]
    pad = 40
    minx, miny = min(xs) - pad, min(ys) - pad
    w, h = max(xs) - minx + pad, max(ys) - miny + pad
    fam = {1: "'Virgil','Comic Sans MS',cursive", 2: "Helvetica,Arial,sans-serif", 3: "'Cascadia Code',monospace"}
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{minx:.0f} {miny:.0f} {w:.0f} {h:.0f}" '
           f'width="{w:.0f}" height="{h:.0f}">',
           '<defs><marker id="ah" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8" markerHeight="8" '
           'orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10" fill="none" stroke="context-stroke" '
           'stroke-width="1.5"/></marker></defs>',
           f'<rect x="{minx}" y="{miny}" width="{w}" height="{h}" fill="{doc["appState"]["viewBackgroundColor"]}"/>']
    esc = lambda s: s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    for el in els:
        if el["type"] == "rectangle":
            dash = ' stroke-dasharray="8 6"' if el["strokeStyle"] == "dashed" else ""
            out.append(f'<rect x="{el["x"]}" y="{el["y"]}" width="{el["width"]}" height="{el["height"]}" '
                       f'rx="16" fill="{el["backgroundColor"]}" stroke="{el["strokeColor"]}" stroke-width="2"{dash}/>')
        elif el["type"] == "arrow":
            (x1, y1), (x2, y2) = el["points"][0], el["points"][-1]
            start = ' marker-start="url(#ah)"' if el["startArrowhead"] else ""
            dash = ' stroke-dasharray="8 6"' if el["strokeStyle"] == "dashed" else ""
            out.append(f'<line x1="{el["x"]+x1}" y1="{el["y"]+y1}" x2="{el["x"]+x2}" y2="{el["y"]+y2}" '
                       f'stroke="{el["strokeColor"]}" stroke-width="2" marker-end="url(#ah)"{start}{dash}/>')
        elif el["type"] == "text":
            anchor = {"left": "start", "center": "middle"}[el["textAlign"]]
            x = el["x"] + (el["width"] / 2 if anchor == "middle" else 0)
            lh = el["fontSize"] * LINE_H
            for i, line in enumerate(el["text"].split("\n")):
                out.append(f'<text x="{x:.1f}" y="{el["y"] + lh * i + el["fontSize"]:.1f}" '
                           f'font-family="{fam[el["fontFamily"]]}" font-size="{el["fontSize"]}" '
                           f'fill="{el["strokeColor"]}" text-anchor="{anchor}">{esc(line)}</text>')
    out.append("</svg>")
    return "\n".join(out)


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-") or "diagram"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("spec")
    ap.add_argument("-o", "--out", default=".", help="output directory")
    ap.add_argument("-n", "--name", help="file name without extension (default: spec 'name' or title)")
    ap.add_argument("--format", choices=["excalidraw", "obsidian", "both"], default="both")
    ap.add_argument("--svg", action="store_true", help="also write a flat SVG preview")
    args = ap.parse_args()

    spec = load_spec(args.spec)
    doc = build(spec)
    name = args.name or spec.get("name") or slug(spec.get("title") or Path(args.spec).stem)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    written = []
    if args.format in ("excalidraw", "both"):
        p = out / f"{name}.excalidraw"
        p.write_text(json.dumps(doc, indent=2))
        written.append(p)
    if args.format in ("obsidian", "both"):
        p = out / f"{name}.excalidraw.md"
        p.write_text(to_obsidian(doc))
        written.append(p)
    if args.svg:
        p = out / f"{name}.svg"
        p.write_text(to_svg(doc))
        written.append(p)
    for p in written:
        print(p)


if __name__ == "__main__":
    main()
