#!/usr/bin/env python3
"""Generate index.html, the landing page for the published site.

The page is a directory and a progress board: one card per team linking to that
team's DAG, mermaid source, standing agenda, and tracker, plus the shared PRD
capability table showing how each team's epics distribute across capabilities.

Every number is counted from the committed tracker snapshots, so the page cannot
drift from the DAGs beside it - re-run this after re-running
build_dependency_dag.py. Nothing here is hand-maintained.

Progress is measured two ways, both from tracker columns:
  evaluated    - 2TS Required is set to something other than TBD, i.e. the epic
                 has been through an evaluation meeting.
  dependencies - Blocking Epics is non-empty, i.e. the epic's dependencies have
                 been captured. This is what gives the DAG its edges.

Standard library only; no third-party dependencies.
"""
from __future__ import annotations

import argparse
import collections
import csv
import html
import json
import os

_HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(_HERE, ".."))
JIRA_BROWSE = "https://asirobots.atlassian.net/browse/"
EMBEDDED_TRACKER = ("https://app.smartsheet.com/sheets/"
                    "gjWCc9QwjFV5qw57vcMf9f9rc4qmXMJvVPrx6VQ1")

# One entry per team. Add the Electronics tracker URL here once the sheet exists.
TEAMS = [
    {
        "name": "Embedded-Core",
        "jira": "VSP-Embedded, project MCHTRNCS",
        "snapshot": "data/tracker-snapshot.csv",
        "dag": "agile-planning/dependency-dag/dependency-dag.html",
        "mmd": "agile-planning/dependency-dag/dependency-dag.mmd",
        "agenda": "agile-planning/meeting-agenda/standingagenda-embedded.html",
        "tracker": EMBEDDED_TRACKER,
    },
    {
        "name": "Electronics",
        "jira": "Electrical Platform, project ET",
        "snapshot": "data/tracker-snapshot-electronics.csv",
        "dag": "agile-planning/dependency-dag-electronics/dependency-dag.html",
        "mmd": "agile-planning/dependency-dag-electronics/dependency-dag.mmd",
        "agenda": "agile-planning/meeting-agenda/standingagenda-electronics.html",
        "tracker": "",
    },
]


def esc(s: str) -> str:
    return html.escape(str(s), quote=True)


def load_rows(path: str) -> list[dict]:
    with open(path, encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def load_json(path: str) -> dict:
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return {}


def pct(part: int, whole: int) -> int:
    return 0 if not whole else round(100 * part / whole)


def evaluated(rows: list[dict]) -> int:
    """Epics that have been through an evaluation meeting."""
    return sum(1 for r in rows if r["2TS Required"].strip() not in ("", "TBD"))


def with_dependencies(rows: list[dict]) -> int:
    return sum(1 for r in rows if r["Blocking Epics"].strip())


def team_card(team: dict, rows: list[dict]) -> str:
    total = len(rows)
    ev, dep = evaluated(rows), with_dependencies(rows)
    n_caps = len({r["Capability"].strip() for r in rows if r["Capability"].strip()})
    tracker = (f'<a href="{esc(team["tracker"])}" target="_blank" '
               f'rel="noopener">Smartsheet tracker &#8599;</a>'
               if team["tracker"] else '<span class="muted">no tracker yet</span>')
    return f'''  <section class="team">
    <h3>{esc(team["name"])}</h3>
    <p class="muted">{esc(team["jira"])} &middot; {total} epics across {n_caps} capabilities</p>
    <dl class="progress">
      <div><dt>Epics evaluated</dt><dd>{ev} / {total} <span class="muted">({pct(ev, total)}%)</span></dd></div>
      <div><dt>Dependencies recorded</dt><dd>{dep} / {total} <span class="muted">({pct(dep, total)}%)</span></dd></div>
    </dl>
    <p class="links">
      <a class="primary" href="{esc(team["dag"])}">Open the dependency DAG &rarr;</a>
      <a href="{esc(team["mmd"])}">Mermaid source</a>
      <a href="{esc(team["agenda"])}">Standing agenda</a>
      {tracker}
    </p>
  </section>'''


def capability_rows(per_team: list[collections.Counter], meta: dict,
                    cap_jira: dict) -> str:
    slugs = sorted(set().union(*per_team) if per_team else set(),
                   key=lambda s: meta.get(s, {}).get("cap_id", "zz"))
    out = []
    for slug in slugs:
        info = meta.get(slug, {})
        key = cap_jira.get(slug, "")
        key_html = (f'<a href="{JIRA_BROWSE}{esc(key)}" target="_blank" '
                    f'rel="noopener">{esc(key)}</a>' if key else "&mdash;")
        cells = "".join(f'<td class="num">{c.get(slug, 0) or "&mdash;"}</td>'
                        for c in per_team)
        out.append(f'    <tr><td class="cap-id">{esc(info.get("cap_id", "?"))}</td>'
                   f'<td>{esc(info.get("title", slug))}</td>{cells}'
                   f'<td class="key">{key_html}</td></tr>')
    return "\n".join(out)


TEMPLATE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>PRAK System Requirements &mdash; Epic Decomposition</title>
<style>
  :root {
    --bg: #ffffff; --fg: #111827; --muted: #667085; --line: #e4e7ec;
    --panel: #fbfcfd; --chip: #f2f4f7; --link: #175cd3; --accent: #175cd3;
  }
  @media (prefers-color-scheme: dark) {
    :root {
      --bg: #0f1319; --fg: #e6e8ec; --muted: #98a2b3; --line: #2a3039;
      --panel: #161b22; --chip: #232a34; --link: #7cb0ff; --accent: #7cb0ff;
    }
  }
  * { box-sizing: border-box; }
  body { font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
         margin: 0 auto; max-width: 60rem; padding: 1.6rem 1.4rem 4rem;
         background: var(--bg); color: var(--fg); line-height: 1.5; }
  a { color: var(--link); }
  .muted { color: var(--muted); font-size: .87rem; }
  header { border-bottom: 1px solid var(--line); padding-bottom: 1rem; margin-bottom: 1.4rem; }
  h1 { font-size: 1.5rem; margin: 0 0 .3rem; }
  h2 { font-size: 1.05rem; margin: 2rem 0 .8rem; padding-bottom: .3rem;
       border-bottom: 1px solid var(--line); }
  h3 { font-size: 1.05rem; margin: 0 0 .2rem; }
  .teams { display: grid; gap: .9rem; grid-template-columns: repeat(auto-fit, minmax(20rem, 1fr)); }
  .team { border: 1px solid var(--line); border-radius: 10px; padding: .9rem 1rem 1rem;
          background: var(--panel); }
  .progress { margin: .7rem 0 .8rem; display: grid; gap: .3rem; }
  .progress div { display: flex; justify-content: space-between; gap: 1rem;
                  border-bottom: 1px dotted var(--line); padding-bottom: .2rem; }
  .progress dt { font-size: .87rem; color: var(--muted); }
  .progress dd { margin: 0; font-size: .87rem; font-variant-numeric: tabular-nums; }
  .links { display: flex; flex-wrap: wrap; gap: .3rem .9rem; margin: 0; font-size: .87rem; }
  .links .primary { font-weight: 600; }
  table { border-collapse: collapse; width: 100%; font-size: .88rem; }
  th, td { text-align: left; padding: .35rem .5rem; border-bottom: 1px solid var(--line); }
  th { font-size: .78rem; text-transform: uppercase; letter-spacing: .03em;
       color: var(--muted); font-weight: 600; }
  td.num, th.num { text-align: right; font-variant-numeric: tabular-nums; }
  .cap-id { font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: .8rem; }
  .key { font-size: .82rem; }
  .wrap { overflow-x: auto; }
  .note { border-left: 3px solid var(--accent); background: var(--panel);
          padding: .6rem .8rem; font-size: .88rem; margin: 1rem 0; }
  footer { margin-top: 2.5rem; padding-top: .8rem; border-top: 1px solid var(--line);
           color: var(--muted); font-size: .82rem; }
</style></head>
<body>
<header>
  <h1>PRAK System Requirements &mdash; Epic Decomposition</h1>
  <p class="muted">Dependency DAGs and decomposition progress for the PRAK epics,
  generated from the trackers of record. Two teams, tracked separately, sharing
  the same PRD Capability Requirements.</p>
</header>

<h2>Teams</h2>
<div class="teams">
__CARDS__
</div>

__PROGRESS_NOTE__

<h2>Shared PRD capabilities</h2>
<p class="muted">Both teams' epics hang off these Jira Initiative issues. This is
the only layer the two trackers share &mdash; no epic appears in both.</p>
<div class="wrap">
<table>
  <thead><tr><th>PRD id</th><th>Capability</th>__TEAM_HEADS__<th>Jira parent</th></tr></thead>
  <tbody>
__CAP_ROWS__
  </tbody>
  <tfoot><tr><th></th><th>Total</th>__TEAM_TOTALS__<th></th></tr></tfoot>
</table>
</div>

<h2>How this is built</h2>
<p class="muted">Nothing here is hand-drawn. <code>tools/build_dependency_dag.py</code>
reads a tracker &mdash; live over the Smartsheet API, or from a CSV export &mdash; and
re-emits the diagram and viewer. Re-run it and the pages reflect current state.
See <a href="README.md">README.md</a> for the commands and
<a href="TODO.md">TODO.md</a> for what is still open.</p>

<footer>
  Counted from <code>data/tracker-snapshot*.csv</code>. Rebuild this page with
  <code>python3 tools/build_index.py</code>.
</footer>
</body></html>
"""

ZERO_NOTE = """<div class="note">
  <b>Progress is genuinely at zero.</b> Epics are evaluated and dependencies
  recorded during the standing meetings; until those happen, both DAGs render
  every epic as unblocked. The Embedded example render
  (<a href="agile-planning/dependency-dag/dependency-dag.example.html">dependency-dag.example.html</a>)
  shows how a populated DAG looks, using sample edges rather than real ones.
</div>"""


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default=os.path.join(ROOT, "index.html"))
    args = ap.parse_args()

    meta = load_json(os.path.join(ROOT, "data", "capability-meta.json"))
    cap_jira = load_json(os.path.join(ROOT, "data", "capability-jira.json"))

    cards, per_team, totals, names = [], [], [], []
    any_progress = False
    for team in TEAMS:
        path = os.path.join(ROOT, team["snapshot"])
        if not os.path.isfile(path):
            print(f"note: {path} missing, skipping {team['name']}")
            continue
        rows = load_rows(path)
        cards.append(team_card(team, rows))
        per_team.append(collections.Counter(
            r["Capability"].strip() for r in rows if r["Capability"].strip()))
        totals.append(len(rows))
        names.append(team["name"])
        any_progress = any_progress or evaluated(rows) or with_dependencies(rows)

    if not cards:
        raise SystemExit("ERROR: no tracker snapshots found - nothing to render.")
    all_rows = sum(totals)

    out = (TEMPLATE
           .replace("__CARDS__", "\n".join(cards))
           .replace("__PROGRESS_NOTE__", "" if any_progress else ZERO_NOTE)
           .replace("__TEAM_HEADS__",
                    "".join(f'<th class="num">{esc(n)}</th>' for n in names))
           .replace("__TEAM_TOTALS__",
                    "".join(f'<th class="num">{t}</th>' for t in totals))
           .replace("__CAP_ROWS__", capability_rows(per_team, meta, cap_jira)))

    with open(args.out, "w", encoding="utf-8") as fh:
        fh.write(out)
    print(f"wrote {args.out}")
    print(f"  {' + '.join(f'{t} {n}' for t, n in zip(names, totals))} "
          f"= {all_rows} epics")


if __name__ == "__main__":
    main()
