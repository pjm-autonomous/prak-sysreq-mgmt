#!/usr/bin/env python3
"""Generate the Embedded-Core epic dependency DAG from the live Smartsheet tracker.

The DAG is derived entirely from the tracker's columns, so it re-populates
whenever the sheet changes: re-run this script (locally, on a schedule, or in
CI) and it re-reads the sheet and re-emits the diagram. Nothing is hand-drawn.

Data sources (pick one):
  --live      Pull the sheet over the Smartsheet REST API. Requires env var
              SMARTSHEET_ACCESS_TOKEN (Smartsheet > Personal Settings > API
              Access > Generate new access token). Sheet id defaults to the
              Embedded-Core tracker; override with --sheet-id.
  --csv PATH  Read a Grid CSV exported from the sheet
              (File > Export > Export to CSV), for offline runs.

Outputs (written to agile-planning/dependency-dag/ by default):
  <basename>.mmd    Mermaid source for the dependency graph
  <basename>.html   Self-contained viewer (open in a browser)

Rendering model
---------------
A tracker row is not automatically a graph node. Only epics that participate in
at least one dependency edge are drawn as a graph; drawing 87 edgeless boxes on
one canvas produces a horizontal band no human can read. So the viewer has two
sections:

  1. Dependency graph  - one mermaid panel per connected component, top-to-bottom,
                         zoomable and pannable. Empty state when no edges exist.
  2. Epic inventory    - a two-level drill-down. Level 1 is one clickable tile per
                         PRD capability, showing its epic count, priority mix, and
                         2TS count. Clicking a tile opens level 2: that capability's
                         epics as cards with full untruncated titles. Searching or
                         filtering cuts across every capability at once.

87 epic cards on one screen is a wall of rows nobody reads, which is why level 1
is the capability, not the epic. The tracker's Capability column holds a capreq
slug, which resolves to product/requirements/product/capreq-<slug>.md in the
prak-v-model checkout (--vmodel) for the PRD id (CAP-nn) and title; the result is
cached to data/capability-meta.json so a checkout without that repo still renders
labels. The capability layer is also where the Embedded and Electronics trackers
meet, so both resolve their groupings against the same capreq files.

The .mmd file carries the dependency graph only; the inventory is a flat list
and a graph is the wrong representation for it.

Dependency convention (the "Blocking Epics" column):
  List the epics that must progress before THIS epic, as a comma/newline/
  semicolon separated list. Each token is an epic id (epic-<slug>) or a Jira
  key (MCHTRNCS-###), optionally tagged (hard) or (soft):
      epic-subscribe-all-stop-broadcaster (hard), MCHTRNCS-220 (soft)
  hard = can't start until the blocker is done (solid edge).
  soft = can start, can't finish until the blocker is done (dashed edge).
  Untagged defaults to hard. Edge points blocker --> dependent.

Standard library only; no third-party dependencies.
"""
from __future__ import annotations

import argparse
import collections
import csv
import html
import json
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone

DEFAULT_SHEET_ID = 8066207570677636
SHEET_URL = "https://app.smartsheet.com/sheets/gjWCc9QwjFV5qw57vcMf9f9rc4qmXMJvVPrx6VQ1"
JIRA_BROWSE = "https://asirobots.atlassian.net/browse/"

# Column titles we read (must match the tracker headers exactly).
COLS = ["Epic", "Jira Key", "Title", "Capability",
        "Baseline Priority", "2TS Required", "Blocking Epics"]

PRIORITY_CLASS = {
    "Must Have": "must", "Should Have": "should",
    "Could Have": "could", "Will Not Have": "wont",
}
PRIORITY_ORDER = ["Must Have", "Should Have", "Could Have", "Will Not Have"]

UNASSIGNED = "unassigned"
UNASSIGNED_LABEL = "No parent capability"

_HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_VMODEL = os.path.normpath(os.path.join(_HERE, "..", "..", "prak-v-model"))
DEFAULT_META_CACHE = os.path.normpath(
    os.path.join(_HERE, "..", "data", "capability-meta.json"))
DEFAULT_CAP_JIRA = os.path.normpath(
    os.path.join(_HERE, "..", "data", "capability-jira.json"))
DEFAULT_MERMAID_BUNDLE = os.path.normpath(
    os.path.join(_HERE, "..", "vendor", "mermaid.min.js"))
MERMAID_CDN = "https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs"


# --------------------------------------------------------------------------- #
# Capability metadata (labels for the drill-down tiles)
# --------------------------------------------------------------------------- #
def _frontmatter(path: str) -> dict:
    """Flat scalar keys from a YAML frontmatter block. Nested keys and lists are
    skipped - we only need id / prd-id / title, all of which are scalars."""
    out: dict[str, str] = {}
    try:
        with open(path, encoding="utf-8") as fh:
            if fh.readline().strip() != "---":
                return out
            for line in fh:
                if line.strip() == "---":
                    break
                match = re.match(r"^([A-Za-z0-9_-]+):[ \t]*(.*)$", line)
                if match and match.group(2).strip():
                    out[match.group(1)] = match.group(2).strip().strip('"').strip("'")
    except OSError:
        pass
    return out


def load_capability_meta(vmodel_dir: str, cache_path: str) -> dict:
    """Map tracker Capability slugs to their PRD id and title.

    The tracker's Capability column holds a capreq slug - the capreq filename
    with the leading "capreq-" dropped - so a slug resolves straight to
    product/requirements/product/capreq-<slug>.md in prak-v-model, which carries
    the PRD id (CAP-nn) and the human title. The resolved map is cached next to
    the tracker snapshot so a checkout without that repo still renders labelled
    tiles. Falls back to bare slugs when neither the repo nor a cache is there.

    This is the layer the Embedded and Electronics trackers share, so both
    trackers resolve their groupings against the same capreq files.
    """
    capreq_dir = os.path.join(vmodel_dir, "product", "requirements", "product")

    if not os.path.isdir(capreq_dir):
        try:
            with open(cache_path, encoding="utf-8") as fh:
                return json.load(fh)
        except (OSError, ValueError):
            print(f"note: {capreq_dir} not found and no cache at {cache_path}; "
                  "capability tiles will show bare slugs", file=sys.stderr)
            return {}

    meta = {}
    for name in sorted(os.listdir(capreq_dir)):
        if not (name.startswith("capreq-") and name.endswith(".md")):
            continue
        front = _frontmatter(os.path.join(capreq_dir, name))
        slug = name[len("capreq-"):-len(".md")]
        meta[slug] = {"cap_id": front.get("prd-id", ""),
                      "title": front.get("title", ""),
                      "priority": front.get("priority", "")}

    try:
        os.makedirs(os.path.dirname(cache_path), exist_ok=True)
        with open(cache_path, "w", encoding="utf-8") as fh:
            json.dump(meta, fh, indent=2, sort_keys=True)
            fh.write("\n")
    except OSError as exc:
        print(f"note: could not write {cache_path}: {exc}", file=sys.stderr)
    return meta


def merge_capability_jira(meta: dict, path: str) -> dict:
    """Attach each capability's Jira issue key, from a slug -> key JSON map.

    A capability is a Jira Initiative issue (e.g. MCHTRNCS-259 for CAP-01), and
    both the Embedded and Electronics epics hang off those same parents - it is
    the one place the two trackers meet. The capreq files carry no Jira key, so
    the mapping comes from this small committed file. Refresh it from a Jira CSV
    export of the PRAK-labelled issues: each Initiative row's Summary is
    "PLAT3-PRD_Rqmts-####: <capability title>", matched to a capreq by title.
    """
    try:
        with open(path, encoding="utf-8") as fh:
            cap_jira = json.load(fh)
    except (OSError, ValueError):
        return meta
    for slug, key in cap_jira.items():
        if slug in meta:
            meta[slug]["jira_key"] = key
        else:
            print(f"note: {path} lists unknown capability {slug!r}", file=sys.stderr)
    return meta


# --------------------------------------------------------------------------- #
# Data loading
# --------------------------------------------------------------------------- #
def load_live(sheet_id: int) -> list[dict]:
    token = os.environ.get("SMARTSHEET_ACCESS_TOKEN")
    if not token:
        sys.exit("ERROR: --live needs SMARTSHEET_ACCESS_TOKEN in the environment.")
    req = urllib.request.Request(
        f"https://api.smartsheet.com/2.0/sheets/{sheet_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            sheet = json.load(resp)
    except urllib.error.HTTPError as exc:
        sys.exit(f"ERROR: Smartsheet API returned {exc.code} {exc.reason}. "
                 "Check SMARTSHEET_ACCESS_TOKEN and --sheet-id.")
    except urllib.error.URLError as exc:
        sys.exit(f"ERROR: could not reach the Smartsheet API: {exc.reason}")

    id2title = {c["id"]: c["title"] for c in sheet["columns"]}
    records = []
    for row in sheet.get("rows", []):
        rec = {t: "" for t in COLS}
        for cell in row.get("cells", []):
            title = id2title.get(cell.get("columnId"))
            if title in rec:
                rec[title] = str(cell.get("value", "") or "")
        records.append(rec)
    return records


def load_csv(path: str) -> list[dict]:
    try:
        with open(path, newline="", encoding="utf-8-sig") as fh:
            rdr = csv.DictReader(fh)
            if rdr.fieldnames is None:
                sys.exit(f"ERROR: {path} is empty.")
            missing = [c for c in COLS if c not in rdr.fieldnames]
            if missing:
                sys.exit(f"ERROR: {path} is missing columns: {', '.join(missing)}")
            return [{t: (row.get(t, "") or "").strip() for t in COLS} for row in rdr]
    except FileNotFoundError:
        sys.exit(f"ERROR: no such CSV: {path}")
    except OSError as exc:
        sys.exit(f"ERROR: could not read {path}: {exc}")


# --------------------------------------------------------------------------- #
# Parsing helpers
# --------------------------------------------------------------------------- #
def node_id(epic: str) -> str:
    return "n_" + re.sub(r"[^0-9a-zA-Z]+", "_", epic.strip()).strip("_")


def parse_blockers(raw: str) -> list[tuple[str, str]]:
    """Return list of (token, kind) where kind is 'hard' or 'soft'."""
    out = []
    for tok in re.split(r"[,\n;]+", raw or ""):
        tok = tok.strip()
        if not tok:
            continue
        kind = "soft" if "soft" in tok.lower() else "hard"
        ref = re.sub(r"\((?:hard|soft)\)", "", tok, flags=re.I)
        ref = re.sub(r"\b(?:hard|soft)\b", "", ref, flags=re.I).strip(" :-–")
        if ref:
            out.append((ref, kind))
    return out


def wrap_label(title: str, width: int = 26) -> str:
    """Wrap a title onto multiple mermaid label lines instead of truncating it."""
    lines, current = [], ""
    for word in title.split():
        if current and len(current) + 1 + len(word) > width:
            lines.append(current)
            current = word
        else:
            current = f"{current} {word}".strip()
    if current:
        lines.append(current)
    return "<br/>".join(lines) or title


def esc_mermaid(s: str) -> str:
    return s.replace('"', "&quot;").replace("[", "(").replace("]", ")")


def capability_of(rec: dict) -> str:
    return rec["Capability"].strip() or UNASSIGNED


def priority_class(rec: dict) -> str:
    return PRIORITY_CLASS.get(rec["Baseline Priority"].strip(), "wont")


def is_2ts(rec: dict) -> bool:
    return rec["2TS Required"].strip().lower() == "yes"


# --------------------------------------------------------------------------- #
# Graph building
# --------------------------------------------------------------------------- #
def build_edges(records: list[dict]) -> list[tuple[str, str, str]]:
    """Resolve the Blocking Epics column into (blocker, dependent, kind) triples."""
    by_epic = {r["Epic"].strip(): r for r in records if r["Epic"].strip()}
    by_jira = {r["Jira Key"].strip().upper(): r for r in records if r["Jira Key"].strip()}

    def resolve(ref: str) -> str | None:
        ref = ref.strip()
        if ref in by_epic:
            return ref
        if ref.upper() in by_jira:
            return by_jira[ref.upper()]["Epic"].strip()
        alt = "epic-" + re.sub(r"^(epic-|sysreq-)", "", ref)
        return alt if alt in by_epic else None

    edges, seen = [], set()
    for rec in records:
        dependent = rec["Epic"].strip()
        for ref, kind in parse_blockers(rec["Blocking Epics"]):
            blocker = resolve(ref)
            if not blocker or blocker == dependent:
                continue
            key = (blocker, dependent, kind)
            if key in seen:
                continue
            seen.add(key)
            edges.append(key)
    return edges


def connected_components(nodes: set[str],
                         edges: list[tuple[str, str, str]]) -> list[list[str]]:
    """Group connected epics into components, treating edges as undirected."""
    adjacency: dict[str, set[str]] = {n: set() for n in nodes}
    for blocker, dependent, _ in edges:
        adjacency[blocker].add(dependent)
        adjacency[dependent].add(blocker)

    seen, components = set(), []
    for start in sorted(nodes):
        if start in seen:
            continue
        stack, group = [start], []
        seen.add(start)
        while stack:
            node = stack.pop()
            group.append(node)
            for neighbour in sorted(adjacency[node]):
                if neighbour not in seen:
                    seen.add(neighbour)
                    stack.append(neighbour)
        components.append(sorted(group))
    # Biggest chains first - they carry the most scheduling risk.
    components.sort(key=lambda g: (-len(g), g[0]))
    return components


CLASSDEFS = """  classDef must fill:#fde4e1,stroke:#b42318,color:#111827;
  classDef should fill:#fff3d6,stroke:#b25e09,color:#111827;
  classDef could fill:#e6f0fd,stroke:#175cd3,color:#111827;
  classDef wont fill:#eceef2,stroke:#667085,color:#111827;
  classDef must_tts fill:#fde4e1,stroke:#7a0b02,stroke-width:4px,color:#111827;
  classDef should_tts fill:#fff3d6,stroke:#7a3c00,stroke-width:4px,color:#111827;
  classDef could_tts fill:#e6f0fd,stroke:#0b3a8f,stroke-width:4px,color:#111827;
  classDef wont_tts fill:#eceef2,stroke:#344054,stroke-width:4px,color:#111827;
  classDef note fill:#f8fafc,stroke:#94a3b8,color:#334155;"""


def component_mermaid(group: list[str],
                      records_by_epic: dict[str, dict],
                      edges: list[tuple[str, str, str]]) -> str:
    """Emit one top-to-bottom flowchart for a single connected component."""
    lines = ["flowchart TB", CLASSDEFS]
    members = set(group)

    by_capability: dict[str, list[str]] = {}
    for epic in group:
        by_capability.setdefault(capability_of(records_by_epic[epic]), []).append(epic)

    node_classes = []
    for init in sorted(by_capability):
        safe = re.sub(r"[^0-9a-zA-Z]+", "_", init) or UNASSIGNED
        # A subgraph wrapper is only worth its border when it groups something.
        wrap = len(by_capability) > 1
        if wrap:
            lines.append(f'  subgraph sg_{safe}["{esc_mermaid(init)}"]')
            lines.append("    direction TB")
        indent = "    " if wrap else "  "
        for epic in by_capability[init]:
            rec = records_by_epic[epic]
            nid = node_id(epic)
            label = esc_mermaid(wrap_label(rec["Title"].strip() or epic))
            jira = rec["Jira Key"].strip()
            if jira:
                label += f"<br/><small>{esc_mermaid(jira)}</small>"
            lines.append(f'{indent}{nid}["{label}"]')
            cls = priority_class(rec) + ("_tts" if is_2ts(rec) else "")
            node_classes.append((nid, cls))
        if wrap:
            lines.append("  end")

    for blocker, dependent, kind in edges:
        if blocker in members and dependent in members:
            arrow = "-->" if kind == "hard" else "-.->"
            lines.append(f"  {node_id(blocker)} {arrow} {node_id(dependent)}")

    for epic in group:
        jira = records_by_epic[epic]["Jira Key"].strip()
        if jira:
            lines.append(f'  click {node_id(epic)} "{JIRA_BROWSE}{jira}" _blank')

    for nid, cls in node_classes:
        lines.append(f"  class {nid} {cls};")

    return "\n".join(lines) + "\n"


EMPTY_GRAPH_MERMAID = """flowchart TB
""" + CLASSDEFS + """
  empty["No dependencies recorded yet<br/><small>fill in the tracker's Blocking Epics column</small>"]
  class empty note;
"""


# --------------------------------------------------------------------------- #
# HTML rendering
# --------------------------------------------------------------------------- #
def esc_html(s: str) -> str:
    return html.escape(s, quote=True)


def capability_sort_key(meta: dict):
    """Order by PRD id (CAP-01, CAP-02, ...) since that is the order the PRD
    itself uses. Slugs with no resolved capreq fall back to alphabetical after
    the resolved ones; unassigned always sorts last."""
    def key(name: str) -> tuple[int, str]:
        if name == UNASSIGNED:
            return (2, "")
        cap_id = meta.get(name, {}).get("cap_id", "")
        return (0, cap_id) if cap_id else (1, name)
    return key


def capability_label(slug: str, meta: dict) -> str:
    if slug == UNASSIGNED:
        return UNASSIGNED_LABEL
    return meta.get(slug, {}).get("title", "") or slug


def capability_code(slug: str, meta: dict) -> str:
    """The PRD id (CAP-nn) when we can resolve it, else the slug itself."""
    if slug == UNASSIGNED:
        return "no capability"
    return meta.get(slug, {}).get("cap_id", "") or slug


def capability_code_html(slug: str, meta: dict, cls: str) -> str:
    """The CAP-nn chip, linked to the capability's Jira Initiative issue when
    known. Rendered as a span inside the tile button, because a nested <a> in a
    <button> is invalid HTML and swallows the tile's own click."""
    code = esc_html(capability_code(slug, meta))
    jira = meta.get(slug, {}).get("jira_key", "")
    title = (f' title="Jira parent {esc_html(jira)} - shared with the other '
             f'team\'s tracker"' if jira else "")
    return f'<span class="{cls}"{title}>{code}</span>'


def capability_jira_html(slug: str, meta: dict) -> str:
    """A real link to the capability's Jira issue, for the level-2 detail head
    where there is no enclosing button to conflict with."""
    jira = meta.get(slug, {}).get("jira_key", "")
    if not jira:
        return ""
    return (f'<a class="cap-jira" href="{JIRA_BROWSE}{esc_html(jira)}" '
            f'target="_blank" rel="noopener">{esc_html(jira)} &#8599;</a>')


def group_by_capability(records: list[dict]) -> dict[str, list[dict]]:
    by_capability: dict[str, list[dict]] = {}
    for rec in records:
        by_capability.setdefault(capability_of(rec), []).append(rec)
    return by_capability


def slug_html(slug: str, meta: dict) -> str:
    """The capreq slug, shown only when it is not already the visible label -
    when the capreq file did not resolve, the slug IS the label."""
    if slug == UNASSIGNED or capability_label(slug, meta) == slug:
        return ""
    return f'<div class="cap">capreq-{esc_html(slug)}</div>'


def render_capability_tiles(records: list[dict], meta: dict) -> str:
    """Level 1 of the inventory: one clickable tile per capability."""
    by_capability = group_by_capability(records)
    out = ['<div class="tiles">']
    for code in sorted(by_capability, key=capability_sort_key(meta)):
        group = by_capability[code]
        counts = collections.Counter(r["Baseline Priority"].strip() for r in group)
        tts = sum(1 for r in group if is_2ts(r))
        unmapped = code == UNASSIGNED
        bars = "".join(
            f'<span class="bar {PRIORITY_CLASS[p]}" style="flex:{counts[p]}" '
            f'title="{counts[p]} {esc_html(p)}"></span>'
            for p in PRIORITY_ORDER if counts[p]
        )
        chips = "".join(
            f'<span class="chip">{counts[p]} {esc_html(p.replace(" Have", ""))}</span>'
            for p in PRIORITY_ORDER if counts[p]
        )
        out.append(
            f'  <button type="button" class="tile{" unmapped" if unmapped else ""}"'
            f' data-capability="{esc_html(code)}">\n'
            f'    <div class="tile-head">'
            f'{capability_code_html(code, meta, "tile-code")}'
            f'<span class="tile-n">{len(group)} '
            f'{"epic" if len(group) == 1 else "epics"}</span></div>\n'
            f'    <h3>{esc_html(capability_label(code, meta))}</h3>\n'
            f'    {slug_html(code, meta)}\n'
            f'    <div class="bars">{bars}</div>\n'
            f'    <div class="tile-meta">{chips}'
            f'<span class="chip">{tts} 2TS</span></div>\n'
            f'  </button>'
        )
    out.append("</div>")
    return "\n".join(out)


def render_cards(records: list[dict], meta: dict) -> str:
    """Level 2 of the inventory: one hidden section of epic cards per capability."""
    by_capability = group_by_capability(records)

    out = []
    for cap in sorted(by_capability, key=capability_sort_key(meta)):
        group = sorted(
            by_capability[cap],
            key=lambda r: (PRIORITY_ORDER.index(r["Baseline Priority"].strip())
                           if r["Baseline Priority"].strip() in PRIORITY_ORDER
                           else len(PRIORITY_ORDER),
                           r["Title"].strip().lower()),
        )
        code_html = ("" if cap == UNASSIGNED
                     else f'<code class="detail-code">'
                          f'{esc_html(capability_code(cap, meta))}</code>'
                          + capability_jira_html(cap, meta))
        out.append(f'<section class="cap-detail" hidden '
                   f'data-capability="{esc_html(cap)}">')
        out.append(
            f'  <div class="detail-head">\n'
            f'    <button type="button" class="back">&larr; All capabilities</button>\n'
            f'    <div class="detail-title">'
            f'<h3>{esc_html(capability_label(cap, meta))}</h3>{code_html}'
            f'<span class="detail-n">{len(group)} '
            f'{"epic" if len(group) == 1 else "epics"}</span></div>\n'
            f'    {slug_html(cap, meta)}\n'
            f'  </div>'
        )
        out.append('  <div class="cards">')
        for rec in group:
            epic = rec["Epic"].strip()
            jira = rec["Jira Key"].strip()
            title = rec["Title"].strip() or epic
            priority = rec["Baseline Priority"].strip() or "unset"
            tts = rec["2TS Required"].strip() or "TBD"
            cls = priority_class(rec) + (" tts" if is_2ts(rec) else "")
            key_html = (f'<a class="key" href="{JIRA_BROWSE}{esc_html(jira)}" '
                        f'target="_blank" rel="noopener">{esc_html(jira)}</a>'
                        if jira else '<span class="key muted">no Jira key</span>')
            out.append(
                f'    <article class="card {cls}" data-epic="{esc_html(epic)}">\n'
                f'      <h3>{esc_html(title)}</h3>\n'
                f'      <div class="card-meta">{key_html}'
                f'<span class="chip">{esc_html(priority)}</span>'
                f'<span class="chip">2TS: {esc_html(tts)}</span></div>\n'
                f'      <code class="slug">{esc_html(epic)}</code>\n'
                f'    </article>'
            )
        out.append("  </div>")
        out.append("</section>")
    return "\n".join(out)


def render_graph_panels(components: list[list[str]],
                        records_by_epic: dict[str, dict],
                        edges: list[tuple[str, str, str]]) -> str:
    if not components:
        return (
            '<div class="empty">\n'
            '  <p><strong>No dependencies recorded yet.</strong></p>\n'
            '  <p>Every epic below is currently unblocked. Edges appear here as soon as the\n'
            "     tracker's <strong>Blocking Epics</strong> column is filled in during the\n"
            '     evaluation meetings - list the epics that must finish first, tagged\n'
            '     <code>(hard)</code> or <code>(soft)</code>, then re-run the generator.</p>\n'
            "</div>"
        )

    panels = []
    for index, group in enumerate(components, start=1):
        member_edges = sum(1 for b, d, _ in edges if b in set(group) and d in set(group))
        diagram = component_mermaid(group, records_by_epic, edges)
        panels.append(
            f'<section class="panel" data-panel="{index}">\n'
            f'  <div class="panel-head">\n'
            f'    <h3>Chain {index}</h3>\n'
            f'    <span class="muted">{len(group)} epics &middot; {member_edges} edges</span>\n'
            f'    <div class="zoom">\n'
            f'      <button type="button" data-zoom="out" title="Zoom out">&minus;</button>\n'
            f'      <button type="button" data-zoom="in" title="Zoom in">+</button>\n'
            f'      <button type="button" data-zoom="fit">Fit</button>\n'
            f'      <button type="button" data-zoom="reset">100%</button>\n'
            f'    </div>\n'
            f'  </div>\n'
            f'  <div class="viewport"><div class="canvas">'
            f'<pre class="mermaid">\n{diagram}</pre></div></div>\n'
            f'</section>'
        )
    return "\n".join(panels)


HTML_TEMPLATE = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__TITLE__</title>
<style>
  :root {
    --bg: #ffffff; --fg: #111827; --muted: #667085; --line: #e4e7ec;
    --panel: #fbfcfd; --chip: #f2f4f7; --link: #175cd3; --accent: #175cd3;
    --must-bg: #fde4e1; --must-br: #b42318;
    --should-bg: #fff3d6; --should-br: #b25e09;
    --could-bg: #e6f0fd; --could-br: #175cd3;
    --wont-bg: #eceef2; --wont-br: #667085;
  }
  @media (prefers-color-scheme: dark) {
    :root {
      --bg: #0f1319; --fg: #e6e8ec; --muted: #98a2b3; --line: #2a3039;
      --panel: #161b22; --chip: #232a34; --link: #7cb0ff; --accent: #7cb0ff;
      --must-bg: #4a1c17; --must-br: #f2705d;
      --should-bg: #4a3410; --should-br: #f5b544;
      --could-bg: #14304f; --could-br: #7cb0ff;
      --wont-bg: #262b33; --wont-br: #98a2b3;
    }
  }
  * { box-sizing: border-box; }
  body { font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
         margin: 0; padding: 1.2rem 1.4rem 3rem; background: var(--bg); color: var(--fg);
         line-height: 1.45; }
  a { color: var(--link); }
  .muted { color: var(--muted); font-size: .85rem; }

  header { border-bottom: 1px solid var(--line); padding-bottom: .8rem; margin-bottom: 1rem; }
  h1 { font-size: 1.2rem; margin: 0 0 .4rem; }
  .stats { display: flex; flex-wrap: wrap; gap: .4rem 1.2rem; align-items: baseline;
           color: var(--muted); font-size: .85rem; }
  .legend { display: flex; flex-wrap: wrap; gap: .35rem; margin-top: .6rem; }
  .legend span { display: inline-block; padding: .1rem .5rem; border-radius: 4px;
                 font-size: .78rem; border: 1px solid; color: var(--fg); }
  .lg-must { background: var(--must-bg); border-color: var(--must-br); }
  .lg-should { background: var(--should-bg); border-color: var(--should-br); }
  .lg-could { background: var(--could-bg); border-color: var(--could-br); }
  .lg-wont { background: var(--wont-bg); border-color: var(--wont-br); }
  .lg-tts { border: 3px solid var(--fg); font-weight: 600; }
  .note { margin-top: .6rem; padding: .5rem .7rem; border-left: 3px solid var(--accent);
          background: var(--panel); font-size: .85rem; }

  .toolbar { display: flex; flex-wrap: wrap; gap: .5rem .7rem; align-items: center;
             margin: 0 0 1.2rem; padding: .6rem .7rem; background: var(--panel);
             border: 1px solid var(--line); border-radius: 8px; position: sticky;
             top: 0; z-index: 20; }
  .toolbar input, .toolbar select, .toolbar button {
      font: inherit; font-size: .87rem; padding: .3rem .5rem; color: var(--fg);
      background: var(--bg); border: 1px solid var(--line); border-radius: 6px; }
  .toolbar input { min-width: 15rem; flex: 1 1 15rem; }
  .toolbar button { cursor: pointer; }
  .toolbar button:hover { border-color: var(--accent); }
  #count { margin-left: auto; color: var(--muted); font-size: .85rem; white-space: nowrap; }

  h2 { font-size: 1rem; margin: 1.8rem 0 .6rem; padding-bottom: .3rem;
       border-bottom: 1px solid var(--line); }
  h2 .muted { font-weight: 400; margin-left: .5rem; }

  .empty { padding: 1rem 1.1rem; border: 1px dashed var(--line); border-radius: 8px;
           background: var(--panel); max-width: 62ch; }
  .empty p { margin: .3rem 0; }
  .empty code { background: var(--chip); padding: .05rem .3rem; border-radius: 4px; }

  .panel { border: 1px solid var(--line); border-radius: 8px; margin-bottom: 1rem;
           background: var(--panel); overflow: hidden; }
  .panel-head { display: flex; align-items: center; gap: .7rem; padding: .45rem .7rem;
                border-bottom: 1px solid var(--line); }
  .panel-head h3 { font-size: .9rem; margin: 0; }
  .zoom { margin-left: auto; display: flex; gap: .25rem; }
  .zoom button { font: inherit; font-size: .8rem; padding: .15rem .5rem; cursor: pointer;
                 background: var(--bg); color: var(--fg); border: 1px solid var(--line);
                 border-radius: 5px; }
  .zoom button:hover { border-color: var(--accent); }
  .viewport { height: 70vh; min-height: 22rem; overflow: hidden; position: relative;
              cursor: grab; background: var(--bg); }
  .viewport.dragging { cursor: grabbing; }
  .canvas { transform-origin: 0 0; padding: 1rem; }
  .canvas pre.mermaid { margin: 0; background: none; }
  .node.dim { opacity: .15; }

  /* ---- inventory level 1: capability tiles ---- */
  .tiles { display: grid; grid-template-columns: repeat(auto-fill, minmax(19rem, 1fr));
           gap: .7rem; }
  .tile { font: inherit; text-align: left; cursor: pointer; color: var(--fg);
          background: var(--panel); border: 1px solid var(--line); border-radius: 10px;
          padding: .7rem .8rem .75rem; display: flex; flex-direction: column;
          gap: .4rem; transition: border-color .12s, transform .12s; }
  .tile:hover, .tile:focus-visible { border-color: var(--accent);
          transform: translateY(-1px); outline: none; }
  .tile.unmapped { border-style: dashed; }
  .tile-head { display: flex; align-items: baseline; gap: .5rem; }
  .tile-code { font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
               font-size: .74rem; letter-spacing: .02em; text-transform: uppercase;
               color: var(--fg); background: var(--chip); border-radius: 999px;
               padding: .1rem .45rem; }
  .tile-n { margin-left: auto; color: var(--muted); font-size: .8rem; }
  .tile h3 { font-size: .98rem; margin: 0; line-height: 1.25; }
  .cap { color: var(--muted); font-size: .78rem; }
  .bars { display: flex; gap: 2px; height: 6px; border-radius: 999px; overflow: hidden;
          background: var(--chip); }
  .bar { display: block; min-width: 3px; }
  .bar.must { background: var(--must-br); }
  .bar.should { background: var(--should-br); }
  .bar.could { background: var(--could-br); }
  .bar.wont { background: var(--wont-br); }
  .tile-meta { display: flex; flex-wrap: wrap; gap: .25rem; }
  .tile-meta .chip { font-size: .7rem; padding: .05rem .4rem; border-radius: 999px;
                     background: var(--chip); color: var(--fg); }

  /* ---- inventory level 2: one capability's epics ---- */
  .cap-detail { border: 1px solid var(--line); border-radius: 10px;
                margin-bottom: .8rem; background: var(--panel); }
  .cap-detail[hidden] { display: none; }
  .detail-head { display: flex; flex-wrap: wrap; align-items: center; gap: .5rem .7rem;
                 padding: .55rem .7rem; border-bottom: 1px solid var(--line); }
  .detail-title { display: flex; flex-wrap: wrap; align-items: baseline; gap: .5rem; }
  .detail-head h3 { font-size: .98rem; margin: 0; }
  .detail-code { font-size: .74rem; background: var(--chip); border-radius: 999px;
                 padding: .1rem .45rem; }
  .detail-n { color: var(--muted); font-size: .8rem; }
  .cap-jira { font-size: .76rem; font-weight: 600; text-decoration: none; }
  .detail-head .cap { flex-basis: 100%; }
  .back { font: inherit; font-size: .82rem; padding: .2rem .55rem; cursor: pointer;
          color: var(--fg); background: var(--bg); border: 1px solid var(--line);
          border-radius: 6px; }
  .back:hover { border-color: var(--accent); }
  .cards { display: grid; grid-template-columns: repeat(auto-fill, minmax(17rem, 1fr));
           gap: .5rem; padding: .7rem; }

  .card { border: 1px solid; border-radius: 6px; padding: .5rem .6rem; color: #111827;
          display: flex; flex-direction: column; gap: .35rem; }
  .card[hidden] { display: none; }
  .card.must { background: var(--must-bg); border-color: var(--must-br); }
  .card.should { background: var(--should-bg); border-color: var(--should-br); }
  .card.could { background: var(--could-bg); border-color: var(--could-br); }
  .card.wont { background: var(--wont-bg); border-color: var(--wont-br); }
  .card.tts { border-width: 3px; }
  @media (prefers-color-scheme: dark) { .card { color: var(--fg); } }
  .card h3 { font-size: .87rem; margin: 0; font-weight: 600; line-height: 1.3; }
  .card-meta { display: flex; flex-wrap: wrap; gap: .3rem; align-items: center; }
  .card .key { font-size: .76rem; font-weight: 600; text-decoration: none; }
  .card .chip { font-size: .7rem; padding: .05rem .35rem; border-radius: 999px;
                background: rgba(127,127,127,.18); }
  .card .slug { font-size: .68rem; opacity: .65; word-break: break-all; }

  @media print {
    .toolbar, .zoom { display: none; }
    body { padding: 0; }
    .viewport { height: auto; overflow: visible; }
    .cards { grid-template-columns: repeat(3, 1fr); }
  }
</style></head>
<body>
<header>
  <h1>__TITLE__</h1>
  <div class="stats">
    <span>__STATS__</span>
    <span>generated __TS__</span>
    __SHEET__
  </div>
  <div class="legend">
    <span class="lg-must">Must</span><span class="lg-should">Should</span>
    <span class="lg-could">Could</span><span class="lg-wont">Won't</span>
    <span class="lg-tts">bold border = 2TS required</span>
  </div>
  <div class="stats" style="margin-top:.4rem">
    <span>solid arrow = hard blocker &middot; dashed arrow = soft blocker &middot;
          edge points blocker &rarr; dependent</span>
  </div>
  __NOTE__
</header>

<div class="toolbar">
  <input id="q" type="search" placeholder="Search title, Jira key, or epic id" autocomplete="off">
  <select id="f-capability"><option value="">All capabilities</option>__CAPABILITY_OPTS__</select>
  <select id="f-priority">
    <option value="">All priorities</option>
    <option>Must Have</option><option>Should Have</option>
    <option>Could Have</option><option>Will Not Have</option>
  </select>
  <select id="f-tts">
    <option value="">2TS: any</option>
    <option value="Yes">2TS: Yes</option>
    <option value="No">2TS: No</option>
    <option value="TBD">2TS: TBD</option>
  </select>
  <button type="button" id="reset">Reset</button>
  <button type="button" id="home" hidden>&larr; All capabilities</button>
  <span id="count"></span>
</div>

<h2>Dependency graph <span class="muted">__GRAPH_CAPTION__</span></h2>
__PANELS__

<h2>Epic inventory <span class="muted" id="inv-caption"></span></h2>
<div id="overview">__TILES__</div>
<div id="details">__CARDS__</div>

__MERMAID_LOADER__
<script id="epic-data" type="application/json">__DATA__</script>
<script type="module">
  /* A vendored bundle, if one was loaded above, has already set globalThis.mermaid;
     otherwise fall back to the CDN so the page still renders. */
  const mermaid = globalThis.mermaid
    ?? (await import("__MERMAID_CDN__")).default;

  const dark = window.matchMedia("(prefers-color-scheme: dark)").matches;
  mermaid.initialize({
    startOnLoad: false,
    securityLevel: "loose",
    theme: dark ? "dark" : "default",
    flowchart: { curve: "basis", nodeSpacing: 45, rankSpacing: 60, useMaxWidth: false },
  });
  await mermaid.run({ querySelector: "pre.mermaid" });

  const EPICS = JSON.parse(document.getElementById("epic-data").textContent);
  const byNodeId = new Map(EPICS.map(e => [e.nid, e]));

  /* ---------- zoom + pan, per panel ---------- */
  for (const panel of document.querySelectorAll(".panel")) {
    const viewport = panel.querySelector(".viewport");
    const canvas = panel.querySelector(".canvas");
    const state = { scale: 1, x: 0, y: 0 };

    const apply = () => {
      canvas.style.transform =
        `translate(${state.x}px, ${state.y}px) scale(${state.scale})`;
    };
    const zoomBy = (factor, originX, originY) => {
      const next = Math.min(4, Math.max(0.1, state.scale * factor));
      const ratio = next / state.scale;
      state.x = originX - (originX - state.x) * ratio;
      state.y = originY - (originY - state.y) * ratio;
      state.scale = next;
      apply();
    };
    const fit = () => {
      const svg = canvas.querySelector("svg");
      if (!svg) return;
      const box = svg.getBoundingClientRect();
      const width = box.width / state.scale;
      const height = box.height / state.scale;
      if (!width || !height) return;
      state.scale = Math.min(viewport.clientWidth / (width + 32),
                             viewport.clientHeight / (height + 32), 1.5);
      state.x = (viewport.clientWidth - width * state.scale) / 2;
      state.y = 12;
      apply();
    };

    viewport.addEventListener("wheel", event => {
      event.preventDefault();
      const rect = viewport.getBoundingClientRect();
      zoomBy(event.deltaY < 0 ? 1.12 : 1 / 1.12,
             event.clientX - rect.left, event.clientY - rect.top);
    }, { passive: false });

    let dragging = false, lastX = 0, lastY = 0;
    viewport.addEventListener("pointerdown", event => {
      if (event.target.closest("a, .node")) return;   // let node links through
      dragging = true; lastX = event.clientX; lastY = event.clientY;
      viewport.classList.add("dragging");
      viewport.setPointerCapture(event.pointerId);
    });
    viewport.addEventListener("pointermove", event => {
      if (!dragging) return;
      state.x += event.clientX - lastX;
      state.y += event.clientY - lastY;
      lastX = event.clientX; lastY = event.clientY;
      apply();
    });
    const endDrag = () => { dragging = false; viewport.classList.remove("dragging"); };
    viewport.addEventListener("pointerup", endDrag);
    viewport.addEventListener("pointercancel", endDrag);

    panel.querySelector(".zoom").addEventListener("click", event => {
      const action = event.target.dataset.zoom;
      if (!action) return;
      const cx = viewport.clientWidth / 2, cy = viewport.clientHeight / 2;
      if (action === "in") zoomBy(1.25, cx, cy);
      else if (action === "out") zoomBy(1 / 1.25, cx, cy);
      else if (action === "fit") fit();
      else { state.scale = 1; state.x = 0; state.y = 0; apply(); }
    });

    fit();
  }

  /* ---------- search + filters ---------- */
  const q = document.getElementById("q");
  const fCapability = document.getElementById("f-capability");
  const fPriority = document.getElementById("f-priority");
  const fTts = document.getElementById("f-tts");
  const count = document.getElementById("count");
  const cards = [...document.querySelectorAll(".card")];
  const cardByEpic = new Map(cards.map(c => [c.dataset.epic, c]));

  const matches = epic => {
    const term = q.value.trim().toLowerCase();
    if (term && !(`${epic.title} ${epic.key} ${epic.epic}`.toLowerCase().includes(term)))
      return false;
    if (fCapability.value && epic.capability !== fCapability.value) return false;
    if (fPriority.value && epic.priority !== fPriority.value) return false;
    if (fTts.value && epic.tts !== fTts.value) return false;
    return true;
  };

  const graphNodes = [...document.querySelectorAll(".panel .node")].map(el => {
    const id = (el.id || "").replace(/^flowchart-/, "").replace(/-\d+$/, "");
    return { el, epic: byNodeId.get(id) };
  }).filter(n => n.epic);

  /* ---------- inventory drill-down: capabilities -> epics ----------
     Three view states, all driven by render():
       overview - the capability tiles, nothing drilled in, no filters
       detail   - one capability's epics, reached by clicking its tile
       search   - a term or filter is active, so every capability that still
                  has a visible card is shown and the tiles step aside      */
  const overview = document.getElementById("overview");
  const detailSections = [...document.querySelectorAll(".cap-detail")];
  const detailCaps = new Set(detailSections.map(s => s.dataset.capability));
  const home = document.getElementById("home");
  const invCaption = document.getElementById("inv-caption");
  let current = "";

  const filtersActive = () =>
    Boolean(q.value.trim() || fCapability.value || fPriority.value || fTts.value);

  const render = () => {
    const searching = filtersActive();
    overview.hidden = searching || Boolean(current);
    home.hidden = !(searching || current);
    for (const section of detailSections) {
      if (searching)
        section.hidden = ![...section.querySelectorAll(".card")].some(c => !c.hidden);
      else
        section.hidden = section.dataset.capability !== current;
    }
    if (searching)
      invCaption.textContent = "matches across all capabilities";
    else if (current)
      invCaption.textContent = "one capability - use Back for all of them";
    else
      invCaption.innerHTML = `${detailSections.length} capabilities &middot; ` +
        `${EPICS.length} epics &middot; pick a capability to see its epics`;
  };

  const applyFilters = () => {
    let shown = 0;
    for (const epic of EPICS) {
      const ok = matches(epic);
      if (ok) shown++;
      const card = cardByEpic.get(epic.epic);
      if (card) card.hidden = !ok;
    }
    for (const node of graphNodes) node.el.classList.toggle("dim", !matches(node.epic));
    count.textContent = `${shown} of ${EPICS.length} epics`;
    render();
  };

  const clearFilters = () => {
    q.value = ""; fCapability.value = ""; fPriority.value = ""; fTts.value = "";
  };

  /* Keep the hash in sync so a drilled-in view is linkable and Back works. */
  const show = cap => {
    current = detailCaps.has(cap) ? cap : "";
    const hash = current ? "#cap=" + encodeURIComponent(current) : "";
    if (hash !== location.hash)
      history.pushState(null, "", hash || location.pathname + location.search);
    applyFilters();
  };

  const readHash = () => {
    const match = /^#cap=(.+)$/.exec(location.hash);
    const wanted = match ? decodeURIComponent(match[1]) : "";
    current = detailCaps.has(wanted) ? wanted : "";
    applyFilters();
  };

  for (const tile of document.querySelectorAll(".tile"))
    tile.addEventListener("click", () => { clearFilters(); show(tile.dataset.capability); });
  for (const back of document.querySelectorAll(".back"))
    back.addEventListener("click", () => { clearFilters(); show(""); });
  home.addEventListener("click", () => { clearFilters(); show(""); });

  for (const control of [q, fCapability, fPriority, fTts])
    control.addEventListener("input", applyFilters);

  document.getElementById("reset").addEventListener("click", () => {
    clearFilters();
    show("");
  });

  window.addEventListener("popstate", readHash);
  window.addEventListener("hashchange", readHash);

  readHash();
</script>
</body></html>
"""


def mermaid_loader(mode: str, bundle: str, outdir: str) -> str:
    """The <script> that makes mermaid available, per --mermaid mode.

    vendor  - reference the committed bundle by a path relative to the output
              file, so a published site serves it same-origin and an opened
              local file still resolves it. Keeps the 3.5 MB blob out of every
              regenerated HTML, which matters because these files are rebuilt
              after every meeting and would otherwise churn git history.
    inline  - embed the bundle, for a single portable file with no sibling
              dependency. Adds ~3.5 MB per output file.
    cdn     - load from jsdelivr at view time. No repo weight, but the page then
              depends on a third-party host being reachable.
    auto    - vendor when the bundle exists, else cdn.
    """
    if mode == "auto":
        mode = "vendor" if os.path.isfile(bundle) else "cdn"
    if mode == "cdn":
        return ""
    if not os.path.isfile(bundle):
        sys.exit(f"ERROR: --mermaid {mode} needs a bundle at {bundle}. "
                 "Download it (see vendor/README.md) or pass --mermaid cdn.")
    if mode == "vendor":
        rel = os.path.relpath(bundle, os.path.abspath(outdir)).replace(os.sep, "/")
        return f'<script src="{esc_html(rel)}"></script>'
    with open(bundle, encoding="utf-8") as fh:
        js = fh.read()
    # "</script" inside a JS string literal would close the tag early.
    return "<script>" + js.replace("</script", r"<\/script") + "</script>"


def build_html(records: list[dict], components: list[list[str]],
               edges: list[tuple[str, str, str]], stats_line: str,
               timestamp: str, note: str, meta: dict,
               title: str, sheet_url: str, mermaid_html: str) -> str:
    records_by_epic = {r["Epic"].strip(): r for r in records}

    capabilities = sorted({capability_of(r) for r in records},
                          key=capability_sort_key(meta))
    capability_opts = "".join(
        f'<option value="{esc_html(c)}">'
        f'{esc_html(capability_code(c, meta))} - {esc_html(capability_label(c, meta))}'
        f'</option>' for c in capabilities)

    data = [{
        "epic": r["Epic"].strip(),
        "nid": node_id(r["Epic"]),
        "key": r["Jira Key"].strip(),
        "title": r["Title"].strip(),
        "capability": capability_of(r),
        "priority": r["Baseline Priority"].strip(),
        "tts": r["2TS Required"].strip() or "TBD",
    } for r in records]

    connected = sum(len(g) for g in components)
    if components:
        caption = (f"{connected} of {len(records)} epics have dependencies "
                   f"&middot; {len(components)} independent "
                   f"{'chain' if len(components) == 1 else 'chains'} "
                   "&middot; scroll to zoom, drag to pan")
    else:
        caption = f"0 of {len(records)} epics have dependencies"

    note_html = (f'<div class="note">{esc_html(note)}</div>') if note else ""

    replacements = {
        "__STATS__": stats_line,
        "__TS__": esc_html(timestamp),
        "__TITLE__": esc_html(title),
        "__MERMAID_LOADER__": mermaid_html,
        "__MERMAID_CDN__": MERMAID_CDN,
        "__SHEET__": (f'<span><a href="{esc_html(sheet_url)}" target="_blank" '
                      f'rel="noopener">open tracker &#8599;</a></span>'
                      if sheet_url else ""),
        "__NOTE__": note_html,
        "__CAPABILITY_OPTS__": capability_opts,
        "__GRAPH_CAPTION__": caption,
        "__PANELS__": render_graph_panels(components, records_by_epic, edges),
        "__NODE_COUNT__": str(len(records)),
        "__TILES__": render_capability_tiles(records, meta),
        "__CARDS__": render_cards(records, meta),
        # </script> inside JSON would close the tag early.
        "__DATA__": json.dumps(data, ensure_ascii=False).replace("</", "<\\/"),
    }
    out = HTML_TEMPLATE
    for token, value in replacements.items():
        out = out.replace(token, value)
    return out


# --------------------------------------------------------------------------- #
# Entry point
# --------------------------------------------------------------------------- #
def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--live", action="store_true", help="pull via Smartsheet API")
    src.add_argument("--csv", metavar="PATH", help="read a Grid CSV export")
    ap.add_argument("--sheet-id", type=int, default=DEFAULT_SHEET_ID)
    ap.add_argument("--sheet-url", default=SHEET_URL,
                    help="tracker permalink for the viewer's 'open tracker' link. "
                         "Pass a different sheet's URL when generating another "
                         "team's DAG, or '' to omit the link entirely.")
    ap.add_argument("--title", default="Embedded-Core Epic Dependency DAG",
                    help="page title and heading (default: %(default)s)")
    here = os.path.dirname(os.path.abspath(__file__))
    ap.add_argument("--outdir", default=os.path.normpath(
        os.path.join(here, "..", "agile-planning", "dependency-dag")))
    ap.add_argument("--basename", default="dependency-dag",
                    help="output file stem (default: dependency-dag)")
    ap.add_argument("--note", default="",
                    help="caption shown under the header, e.g. an EXAMPLE disclaimer")
    ap.add_argument("--timestamp", default="", help="override generated-at stamp")
    ap.add_argument("--vmodel", default=DEFAULT_VMODEL,
                    help="prak-v-model checkout, read for capability titles and "
                         "PRD ids (default: %(default)s)")
    ap.add_argument("--mermaid", choices=["auto", "cdn", "vendor", "inline"],
                    default="auto",
                    help="how the viewer loads mermaid: vendor (reference the "
                         "committed bundle), inline (embed it), cdn (jsdelivr), "
                         "or auto = vendor when the bundle exists (default)")
    ap.add_argument("--mermaid-bundle", default=DEFAULT_MERMAID_BUNDLE,
                    help="path to the mermaid UMD bundle (default: %(default)s)")
    ap.add_argument("--capability-jira", default=DEFAULT_CAP_JIRA,
                    help="JSON map of capability slug -> Jira Initiative key, "
                         "used to link each capability to its shared parent issue")
    ap.add_argument("--meta-cache", default=DEFAULT_META_CACHE,
                    help="where the resolved capability titles are cached so runs "
                         "without --vmodel still render labels")
    args = ap.parse_args()

    meta = merge_capability_jira(
        load_capability_meta(args.vmodel, args.meta_cache), args.capability_jira)
    records = load_live(args.sheet_id) if args.live else load_csv(args.csv)
    records = [r for r in records if r["Epic"].strip()]
    if not records:
        sys.exit("ERROR: no rows with an Epic id - nothing to render.")

    records_by_epic = {r["Epic"].strip(): r for r in records}
    edges = build_edges(records)
    connected_nodes = {n for edge in edges for n in edge[:2]}
    components = connected_components(connected_nodes, edges)

    hard = sum(1 for e in edges if e[2] == "hard")
    soft = len(edges) - hard
    n_capabilities = len({capability_of(r) for r in records})
    stats_line = (f"{len(records)} epics &middot; {n_capabilities} capabilities "
                  f"&middot; {hard} hard + {soft} soft edges")

    timestamp = args.timestamp or datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    if components:
        mermaid_src = "\n\n".join(
            f"%% chain {i}\n" + component_mermaid(g, records_by_epic, edges)
            for i, g in enumerate(components, start=1))
    else:
        mermaid_src = ("%% No dependencies recorded in the tracker's Blocking Epics "
                       "column yet.\n%% All " + str(len(records)) +
                       " epics are unblocked; see the HTML viewer for the inventory.\n"
                       + EMPTY_GRAPH_MERMAID)

    os.makedirs(args.outdir, exist_ok=True)
    mmd_path = os.path.join(args.outdir, f"{args.basename}.mmd")
    html_path = os.path.join(args.outdir, f"{args.basename}.html")
    with open(mmd_path, "w", encoding="utf-8") as fh:
        fh.write(mermaid_src)
    with open(html_path, "w", encoding="utf-8") as fh:
        fh.write(build_html(records, components, edges, stats_line,
                            timestamp, args.note, meta,
                            args.title, args.sheet_url,
                            mermaid_loader(args.mermaid, args.mermaid_bundle,
                                           args.outdir)))

    print(f"wrote {mmd_path}")
    print(f"wrote {html_path}")
    print(f"  {len(records)} epics, {hard} hard + {soft} soft edges, "
          f"{len(connected_nodes)} in {len(components)} chain(s), "
          f"{n_capabilities} capabilities")


if __name__ == "__main__":
    main()
