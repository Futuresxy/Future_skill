#!/usr/bin/env python3
"""Render an evidence-backed architecture JSON as editable SVG. Standard library only."""
import argparse
import json
import math
import re
from pathlib import Path
from xml.sax.saxutils import escape

PALETTE = {
    "backbone": "#2997EC", "attention": "#FF9E10", "ffn": "#91CC46",
    "moe": "#537DFA", "vision": "#FF7777", "detail": "#8035A5",
    "cache": "#ED232A", "neutral": "#444444",
}
ID = re.compile(r"[A-Za-z_][A-Za-z0-9_.-]*\Z")
COLOR = re.compile(r"#[0-9a-fA-F]{6}\Z")


def number(value, context):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"{context}: expected finite number")
    return value


def color(value):
    if value in PALETTE:
        return PALETTE[value]
    if isinstance(value, str) and COLOR.fullmatch(value):
        return value
    raise ValueError(f"Unknown role/color: {value!r}")


def point(p, width, height, context):
    if not isinstance(p, list) or len(p) != 2:
        raise ValueError(f"{context}: expected [x, y]")
    x, y = (number(v, context) for v in p)
    if not (0 <= x <= width and 0 <= y <= height):
        raise ValueError(f"{context}: point outside canvas")
    return x, y


def validate(spec):
    for key in ("title", "source_note"):
        if not isinstance(spec.get(key), str) or not spec[key].strip():
            raise ValueError(f"Missing {key}")
    width, height = (number(spec[k], k) for k in ("width", "height"))
    if width <= 0 or height <= 0:
        raise ValueError("Canvas dimensions must be positive")
    ids, nodes = {"arrow", "diagram-title"}, {}
    for kind in ("panels", "nodes", "edges", "labels"):
        items = spec.get(kind, [])
        if not isinstance(items, list):
            raise ValueError(f"{kind}: expected array")
        for obj in items:
            ident = obj.get("id", "")
            if not isinstance(ident, str) or not ID.fullmatch(ident) or ident in ids:
                raise ValueError(f"Invalid/duplicate ID: {ident!r}")
            ids.add(ident)
            color(obj.get("role", "neutral"))
            if obj.get("anchor", "start") not in ("start", "middle", "end"):
                raise ValueError(f"{ident}: invalid text anchor")
            if "font_size" in obj and number(obj["font_size"], ident) <= 0:
                raise ValueError(f"{ident}: font_size must be positive")
            if kind in ("panels", "nodes"):
                x, y = point([obj.get("x"), obj.get("y")], width, height, ident)
                w, h = (number(obj.get(k), ident) for k in ("w", "h"))
                if w <= 0 or h <= 0 or x + w > width or y + h > height:
                    raise ValueError(f"{ident}: invalid box/outside canvas")
            if kind == "nodes":
                if obj.get("shape", "box") not in ("box", "outline", "add", "multiply", "up", "down"):
                    raise ValueError(f"{ident}: unsupported shape")
                nodes[ident] = obj
            if kind == "labels":
                point([obj.get("x"), obj.get("y")], width, height, ident)
            if kind in ("nodes", "edges"):
                if kind == "edges" and obj.get("kind", "data") == "callout":
                    continue
                if not isinstance(obj.get("evidence"), str) or not obj["evidence"].strip():
                    raise ValueError(f"{ident}: evidence required")
    if not nodes:
        raise ValueError("At least one node is required")
    for e in spec.get("edges", []):
        ident = e["id"]
        if e.get("kind", "data") not in ("data", "residual", "route", "state", "optional", "callout"):
            raise ValueError(f"{ident}: invalid edge kind")
        for key in ("from", "to"):
            if key in e and e[key] not in nodes:
                raise ValueError(f"{ident}: missing node {e[key]!r}")
        if "points" in e:
            if not isinstance(e["points"], list) or len(e["points"]) < 2:
                raise ValueError(f"{ident}: need at least two points")
            for p in e["points"]:
                point(p, width, height, ident)
        elif not all(k in e for k in ("from", "to")):
            raise ValueError(f"{ident}: need points or from/to")
        if "label" in e and not all(k in e for k in ("label_x", "label_y")):
            raise ValueError(f"{ident}: label requires label_x/label_y")
        if "label" in e:
            point([e["label_x"], e["label_y"]], width, height, ident)
        for key in ("from_port", "to_port"):
            if key in e and e[key] not in ("top", "bottom", "left", "right"):
                raise ValueError(f"{ident}: invalid port")
    return nodes


def text(x, y, content, size=17, fill="#222222", anchor="middle", bold=False, ident=None):
    """Baseline-based multi-line text. Font metrics are checked during visual QA."""
    attrs = f' id="{ident}"' if ident else ""
    weight = "700" if bold else "400"
    lines = str(content).split("\n")
    spans = "".join(f'<tspan x="{x}" dy="{0 if i == 0 else size * 1.25}">{escape(line)}</tspan>'
                    for i, line in enumerate(lines))
    return (f'<text{attrs} x="{x}" y="{y}" text-anchor="{anchor}" font-size="{size}" '
            f'font-weight="{weight}" fill="{fill}">{spans}</text>')


def port(node, side):
    x, y, w, h = (node[k] for k in ("x", "y", "w", "h"))
    return {"top": (x + w / 2, y), "bottom": (x + w / 2, y + h),
            "left": (x, y + h / 2), "right": (x + w, y + h / 2)}[side]


def title_evidence(obj):
    return f'<title>{escape(obj.get("evidence", obj.get("label", "")))}</title>'


def render(spec):
    nodes = validate(spec)
    w, h = spec["width"], spec["height"]
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-labelledby="diagram-title">',
           f'<title id="diagram-title">{escape(spec["title"])}</title>',
           '<defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill="context-stroke"/></marker></defs>',
           f'<rect width="{w}" height="{h}" fill="#FFFFFF"/>',
           '<g font-family="Arial, Noto Sans CJK SC, PingFang SC, Microsoft YaHei, sans-serif">',
           text(w / 2, 46, spec["title"], 32, bold=True),
           text(w / 2, 76, spec["source_note"], 15, fill="#555555")]
    for p in spec.get("panels", []):
        c = color(p.get("role", "neutral"))
        out.extend([f'<g id="{p["id"]}">', title_evidence(p),
                    f'<rect x="{p["x"]}" y="{p["y"]}" width="{p["w"]}" height="{p["h"]}" rx="10" fill="none" stroke="{c}" stroke-width="1.5" stroke-dasharray="8 5"/>',
                    text(p["x"] + 12, p["y"] + 27, p.get("label", ""), 22, c, "start", True), '</g>'])
    # Edges are behind nodes; explicit waypoints keep crossings under author control.
    for e in spec.get("edges", []):
        kind = e.get("kind", "data")
        c = color(e.get("role", "neutral"))
        pts = e.get("points")
        if pts is None:
            a = port(nodes[e["from"]], e.get("from_port", "top"))
            b = port(nodes[e["to"]], e.get("to_port", "bottom"))
            pts = [a, b] if a[0] == b[0] or a[1] == b[1] else [a, (a[0], (a[1]+b[1])/2), (b[0], (a[1]+b[1])/2), b]
        dash = ' stroke-dasharray="8 5"' if kind in ("callout", "route", "optional") else ""
        marker = '' if kind == "callout" else ' marker-end="url(#arrow)"'
        coords = " ".join(f"{x},{y}" for x, y in pts)
        out.extend([f'<g id="{e["id"]}">', title_evidence(e),
                    f'<polyline points="{coords}" fill="none" stroke="{c}" stroke-width="1.6" stroke-linejoin="round"{dash}{marker}/>', '</g>'])
    for n in nodes.values():
        x, y, nw, nh = (n[k] for k in ("x", "y", "w", "h"))
        c = color(n.get("role", "backbone"))
        shape = n.get("shape", "box")
        out.extend([f'<g id="{n["id"]}">', title_evidence(n)])
        if shape in ("add", "multiply"):
            out.append(f'<ellipse cx="{x+nw/2}" cy="{y+nh/2}" rx="{nw/2}" ry="{nh/2}" fill="{c}" stroke="#333333" stroke-width="1.3"/>')
        elif shape in ("up", "down"):
            corners = [(x,y),(x+nw,y),(x+nw*.88,y+nh),(x+nw*.12,y+nh)] if shape == "up" else [(x+nw*.12,y),(x+nw*.88,y),(x+nw,y+nh),(x,y+nh)]
            out.append(f'<polygon points="{" ".join(f"{a},{b}" for a,b in corners)}" fill="{c}"/>')
        else:
            fill, dash = ("#FFFFFF", ' stroke-dasharray="8 5"') if shape == "outline" else (c, "")
            out.append(f'<rect x="{x}" y="{y}" width="{nw}" height="{nh}" rx="8" fill="{fill}" stroke="{c}" stroke-width="1.5"{dash}/>')
        label = {"add": "+", "multiply": "×"}.get(shape, n.get("label", ""))
        size = n.get("font_size", 18 if shape not in ("add", "multiply") else 26)
        # Light orange/green/red fill needs dark text for readable contrast.
        fg = c if shape == "outline" else ("#FFFFFF" if n.get("role") in ("backbone", "moe", "detail", "neutral", "cache") else "#202020")
        if "text_color" in n:
            fg = color(n["text_color"])
        base = y + nh/2 + size*.35 - (len(str(label).split("\n"))-1)*size*.625
        out.extend([text(x+nw/2, base, label, size, fg, bold=shape == "outline"), '</g>'])
    # Labels are last so annotation positions are explicit and visible.
    for e in spec.get("edges", []):
        if "label" in e:
            out.append(text(e["label_x"], e["label_y"], e["label"], e.get("font_size",15), anchor=e.get("anchor","start")))
    for label in spec.get("labels", []):
        out.append(text(label["x"], label["y"], label["text"], label.get("font_size",16),
                        color(label.get("role","neutral")), label.get("anchor","start"), label.get("bold",False), label["id"]))
    out.extend(['</g>', '</svg>'])
    return "\n".join(out) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    try:
        spec = json.loads(args.input.read_text(encoding="utf-8"))
        svg = render(spec)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(svg, encoding="utf-8")
    except (OSError, ValueError, KeyError, TypeError) as exc:
        parser.exit(1, f"render_diagram: {exc}\n")
    print(f"SVG: {args.output}")
    print("Rasterize and inspect the image; schema validation does not verify model semantics or layout.")


if __name__ == "__main__":
    main()
