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
  dependencies - Blocking Issues is non-empty, i.e. the epic's dependencies have
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
import subprocess
import sys
from datetime import datetime, timezone

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
import teams as team_registry  # noqa: E402
from build_dependency_dag import COLUMN_ALIASES, parse_blockers  # noqa: E402

ROOT = team_registry.ROOT
JIRA_BROWSE = "https://asirobots.atlassian.net/browse/"
# Repo blob base, so the "how this is built" links render as markdown on
# github.com instead of being served raw by GitHub Pages.
REPO_BLOB = "https://github.com/pjm-autonomous/prak-sysreq-mgmt/blob/main/"

# Teams come from tools/teams.py so a sheet url or output path is defined once.
# The per-team paths a DAG produces are derived from that entry's outdir.
TEAMS = [
    {
        **cfg,
        "slug": slug,
        "dag": f"{cfg['outdir']}/{cfg['basename']}.html",
        "mmd": f"{cfg['outdir']}/{cfg['basename']}.mmd",
        "tracker": cfg["sheet_url"],
    }
    for slug, cfg in ((s, team_registry.team(s)) for s in team_registry.ORDER)
]
EXAMPLE = team_registry.team(team_registry.EXAMPLE)
EXAMPLE_DAG = f"{EXAMPLE['outdir']}/{EXAMPLE['basename']}.html"


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
    return sum(1 for r in rows if r["Blocking Issues"].strip())


def provisional(rows: list[dict]) -> int:
    """Of the recorded dependencies, how many are still marked [guess] - a
    working assumption from before an evaluation meeting, not a confirmed edge.
    The DAG viewer labels these 'guess'; the landing page must not present them
    as settled."""
    return sum(1 for r in rows
               if r["Blocking Issues"].strip() and "[guess]" in r["Blocking Issues"])


def team_card(team: dict, rows: list[dict]) -> str:
    total = len(rows)
    ev, dep = evaluated(rows), with_dependencies(rows)
    prov = provisional(rows)
    dep_caveat = ""
    if prov:
        which = "all provisional" if prov == dep else f"{prov} provisional"
        dep_caveat = (' <span class="muted" title="Marked [guess] in the tracker: '
                      'a working assumption, not yet confirmed in an evaluation '
                      f'meeting.">&middot; {which}</span>')
    n_caps = len({r["Capability"].strip() for r in rows if r["Capability"].strip()})
    tracker = (f'<a href="{esc(team["tracker"])}" target="_blank" '
               f'rel="noopener">Smartsheet tracker &#8599;</a>'
               if team["tracker"] else '<span class="muted">no tracker yet</span>')
    return f'''  <section class="team">
    <h3>{esc(team["name"])}</h3>
    <p class="muted">{esc(team["jira"])} &middot; {total} epics across {n_caps} capabilities</p>
    <dl class="progress">
      <div><dt>Epics evaluated</dt><dd>{ev} / {total} <span class="muted">({pct(ev, total)}%)</span></dd></div>
      <div><dt>Dependencies recorded</dt><dd>{dep} / {total} <span class="muted">({pct(dep, total)}%)</span>{dep_caveat}</dd></div>
    </dl>
    <p class="links">
      <a class="primary" href="{esc(team["dag"])}">Open the dependency DAG &rarr;</a>
      <a href="{esc(team["mmd"])}">Mermaid source</a>
      <a href="{esc(team["agenda"])}">Standing agenda</a>
      {tracker}
    </p>
  </section>'''


def cross_team_edges(loaded: dict) -> list[dict]:
    """Every blocker that leaves the tracker it was recorded in.

    This is the one thing the per-team DAGs structurally cannot show. A blocker
    on another team's epic renders inside the dependent team's viewer, under
    "other tracker" - so the team that is *blocking* has no reason to open the
    page where their obligation appears. Embedded has been waiting on ODOA-5527
    since before ODOA had a tracker, and nobody on ODOA was told.
    """
    owner = {epic: team for team, rows in loaded.items()
             for epic in (r["Epic"].strip() for r in rows)}
    edges = []
    for team, rows in loaded.items():
        for row in rows:
            for ref, kind, provisional, hint in parse_blockers(
                    row.get("Blocking Issues", "")):
                if owner.get(ref) == team:
                    continue                       # internal, the DAG shows it
                edges.append({
                    "dependent_team": team,
                    "dependent": row["Epic"].strip(),
                    "dependent_title": row.get("Title", "").strip(),
                    "blocker": ref,
                    "blocker_team": owner.get(ref) or (hint or "not yet tracked"),
                    "resolved": ref in owner,
                    "kind": kind,
                    "provisional": provisional,
                })
    return sorted(edges, key=lambda e: (e["blocker_team"], e["blocker"]))


def cross_team_html(edges: list[dict]) -> str:
    if not edges:
        return ""
    rows = []
    for e in edges:
        blocker = esc(e["blocker"])
        if not e["resolved"]:
            blocker += ' <span class="muted">(no tracker)</span>'
        tags = []
        if e["kind"] == "soft":
            tags.append("soft")
        if e["provisional"]:
            tags.append("guess")
        tag_html = (f' <span class="muted">&middot; {" &middot; ".join(tags)}</span>'
                    if tags else "")
        rows.append(
            f'    <tr><td><b>{esc(e["blocker_team"])}</b></td>'
            f'<td class="cap-id">{blocker}</td>'
            f'<td>{esc(e["dependent_team"])}</td>'
            f'<td>{esc(e["dependent_title"] or e["dependent"])}{tag_html}</td></tr>')
    return f"""<h2>Cross-team dependencies</h2>
<p class="muted">Work one team is waiting on another to finish. Each of these
appears inside the <em>dependent</em> team's DAG as an external node &mdash; so
without this table the blocking team has no reason to ever see it.
<b>{len(edges)}</b> recorded.</p>
<div class="wrap">
<table>
  <thead><tr><th>Blocking team</th><th>Blocking issue</th>
             <th>Waiting team</th><th>Waiting on it</th></tr></thead>
  <tbody>
{chr(10).join(rows)}
  </tbody>
</table>
</div>
"""


def pending_card(team: dict) -> str:
    """A team that is registered and has a container but no tracker yet.

    Rendering it as a real card with zeroes would claim 0% progress against a
    denominator nobody has established. The card states the actual position:
    the scope is queued, and which workflow steps produce the missing pieces.
    """
    return f'''  <section class="team pending">
    <h3>{esc(team["name"])} <span class="chip">not yet onboarded</span></h3>
    <p class="muted">{esc(team["jira"])} &middot; no tracker of record yet</p>
    <p class="muted">Container reserved at <code>{esc(team["outdir"])}/</code> and
    <code>{esc(team["snapshot"])}</code>. The scope has to be decomposed and imported
    (<a href="__BLOB__WORKFLOW.md">WORKFLOW.md</a> steps 1&ndash;11), then its
    Smartsheet tracker stood up and connected (steps 12&ndash;14), before a DAG and
    progress numbers exist.</p>
  </section>'''


def git(*args: str) -> str:
    """Run git in the repo, returning "" when it cannot answer.

    Everything here degrades to no digest rather than a failed build: CI checks
    out at depth 1 by default, so the history this needs may simply not be
    present.
    """
    try:
        out = subprocess.run(("git",) + args, cwd=ROOT, capture_output=True,
                             text=True, timeout=30)
        return out.stdout if out.returncode == 0 else ""
    except (OSError, subprocess.SubprocessError):
        return ""


# Columns worth reporting on. Title and Jira Key churn without meaning anything
# for progress; these three are what the standing meetings actually move.
DIGEST_COLS = ("2TS Required", "Blocking Issues", "Eval Status")


def recent_changes(days: int) -> tuple[list[str], str]:
    """What moved in the snapshots over the last `days`. ([lines], note)."""
    since = git("log", f"--since={days} days ago", "--format=%H", "--reverse",
                "--", "data")
    commits = [c for c in since.splitlines() if c.strip()]
    if not commits:
        return [], ""
    # Baseline is the parent of the oldest commit in the window when that is
    # readable, else the earliest commit in the window where the file exists.
    # A path can appear or move mid-window - the per-team containers landed
    # that way - and anchoring to one fixed commit silently yields no digest.
    candidates = [git("rev-parse", f"{commits[0]}~1").strip() or commits[0]]
    candidates += commits

    lines = []
    base_used = candidates[0]
    for team in TEAMS:
        path = team["snapshot"]
        before_raw = ""
        for candidate in candidates:
            before_raw = git("show", f"{candidate}:{path}")
            if before_raw:
                base_used = candidate
                break
        if not before_raw:
            continue                                  # new team in this window
        try:
            after = {r["Epic"].strip(): r for r in load_rows(
                os.path.join(ROOT, path))}
        except OSError:
            continue
        reader = csv.DictReader(before_raw.splitlines())
        historical = list(reader.fieldnames or [])
        # Translate headers the baseline used under an older name, so a rename
        # does not read as every row changing.
        before = {}
        for raw in reader:
            row = {COLUMN_ALIASES.get(k, k): v for k, v in raw.items()}
            if row.get("Epic", "").strip():
                before[row["Epic"].strip()] = row
        comparable = {COLUMN_ALIASES.get(h, h) for h in historical}

        added = sorted(set(after) - set(before))
        removed = sorted(set(before) - set(after))
        moved = {c: 0 for c in DIGEST_COLS}
        for epic in set(after) & set(before):
            for col in DIGEST_COLS:
                # A column absent from the baseline cannot have "changed" - it
                # was introduced. Comparing it would report the whole tracker.
                if col not in comparable:
                    continue
                if (before[epic].get(col) or "").strip() != (after[epic].get(col) or "").strip():
                    moved[col] += 1
        bits = []
        if added:
            bits.append(f"{len(added)} epic(s) added")
        if removed:
            bits.append(f"{len(removed)} removed")
        for col, n in moved.items():
            if n:
                bits.append(f"{n} &times; {esc(col)}")
        if bits:
            lines.append(f"<b>{esc(team['name'])}</b>: " + ", ".join(bits))
    return lines, base_used[:7]


def digest_html(days: int) -> str:
    lines, base = recent_changes(days)
    if not lines:
        return ""
    items = "".join(f"<li>{ln}</li>" for ln in lines)
    return f"""<h2>What changed in the last {days} days</h2>
<p class="muted">Counted by diffing the committed snapshots against
<code>{esc(base)}</code>. Only the columns the standing meetings move are
reported &mdash; 2TS decisions, dependencies, and evaluation status.</p>
<ul class="digest">{items}</ul>
"""


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
  .team.pending { border-style: dashed; background: transparent; }
  .team.pending h3 { color: var(--muted); }
  .chip { display: inline-block; vertical-align: middle; background: var(--chip);
          color: var(--muted); border-radius: 999px; padding: .1rem .5rem;
          font-size: .7rem; font-weight: 600; text-transform: uppercase;
          letter-spacing: .04em; }
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
  .digest { margin: .2rem 0 0; padding-left: 1.1rem; font-size: .9rem; }
  .digest li { margin: .15rem 0; }
  .note { border-left: 3px solid var(--accent); background: var(--panel);
          padding: .6rem .8rem; font-size: .88rem; margin: 1rem 0; }
  footer { margin-top: 2.5rem; padding-top: .8rem; border-top: 1px solid var(--line);
           color: var(--muted); font-size: .82rem; }
</style></head>
<body>
<header>
  <h1>PRAK System Requirements &mdash; Epic Decomposition</h1>
  <p class="muted">Dependency DAGs and decomposition progress for the PRAK epics,
  generated from the trackers of record. __N_TEAMS__ teams, tracked separately,
  sharing the same PRD Capability Requirements.</p>
</header>

<h2>Teams</h2>
<p class="muted"><b>Evaluated</b> &mdash; the epic has been through an evaluation
meeting, so its 2TS need is decided. <b>Dependencies recorded</b> &mdash; its
blocking epics have been captured in the tracker; <i>provisional</i> ones are
recorded but still marked a guess, not yet confirmed in a meeting.</p>
<div class="teams">
__CARDS__
</div>

__PROGRESS_NOTE__

__DIGEST__

__CROSS_TEAM__

<h2>Shared PRD capabilities</h2>
<p class="muted">Every team's epics hang off these Jira Initiative issues. This is
the only layer the trackers share &mdash; no epic appears in two of them.</p>
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
See <a href="__BLOB__README.md">README.md</a> for the commands,
<a href="__BLOB__PUBLISHING.md">PUBLISHING.md</a> for how the pages are released,
and <a href="__BLOB__TODO.md">TODO.md</a> for what is still open.</p>

<footer>
  Updated __UPDATED__ &middot; counted from <code>data/&lt;team&gt;/tracker-snapshot.csv</code>.
  Rebuild this page with <code>python3 tools/build_index.py</code>.
</footer>
</body></html>
"""

ZERO_NOTE = """<div class="note">
  <b>Progress is genuinely at zero.</b> Epics are evaluated and dependencies
  recorded during the standing meetings; until those happen, every DAG renders
  each epic as unblocked. The example render
  (<a href="__EXAMPLE_DAG__">__EXAMPLE_NAME__</a>)
  shows how a populated DAG looks, using sample edges rather than real ones.
</div>"""


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default=os.path.join(ROOT, "index.html"))
    ap.add_argument("--digest-days", type=int, default=7,
                    help="window for the 'what changed' digest (0 disables)")
    ap.add_argument("--timestamp", default="",
                    help="override the 'Updated' stamp (default: today, UTC)")
    args = ap.parse_args()
    updated = args.timestamp or datetime.now(timezone.utc).strftime("%Y-%m-%d")

    meta = load_json(team_registry.abspath(team_registry.CAPABILITY_META))
    cap_jira = load_json(team_registry.abspath(team_registry.CAPABILITY_JIRA))

    cards, per_team, totals, names, pending = [], [], [], [], []
    loaded: dict[str, list[dict]] = {}
    any_progress = False
    for team in TEAMS:
        path = os.path.join(ROOT, team["snapshot"])
        if not os.path.isfile(path):
            # Registered without a tracker is the expected state for a team
            # still queued for decomposition - render the container, not a
            # fabricated 0/0. A missing snapshot for an onboarded team is a
            # real problem, so that one is called out as an error.
            if team_registry.onboarded(team):
                raise SystemExit(
                    f"ERROR: {team['name']} is onboarded (sheet "
                    f"{team['sheet_id']}) but {team['snapshot']} is missing. "
                    f"Run: python3 tools/export_snapshot.py --team {team['slug']}")
            cards.append(pending_card(team))
            pending.append(team["name"])
            continue
        rows = load_rows(path)
        loaded[team["name"]] = rows
        cards.append(team_card(team, rows))
        per_team.append(collections.Counter(
            r["Capability"].strip() for r in rows if r["Capability"].strip()))
        totals.append(len(rows))
        names.append(team["name"])
        any_progress = any_progress or evaluated(rows) or with_dependencies(rows)

    if not names:
        raise SystemExit("ERROR: no tracker snapshots found - nothing to render.")
    all_rows = sum(totals)

    out = (TEMPLATE
           .replace("__CARDS__", "\n".join(cards))
           .replace("__PROGRESS_NOTE__", "" if any_progress else ZERO_NOTE)
           .replace("__TEAM_HEADS__",
                    "".join(f'<th class="num">{esc(n)}</th>' for n in names))
           .replace("__TEAM_TOTALS__",
                    "".join(f'<th class="num">{t}</th>' for t in totals))
           .replace("__CROSS_TEAM__", cross_team_html(cross_team_edges(loaded)))
           .replace("__DIGEST__", digest_html(args.digest_days))
           .replace("__CAP_ROWS__", capability_rows(per_team, meta, cap_jira))
           .replace("__EXAMPLE_DAG__", esc(EXAMPLE_DAG))
           .replace("__EXAMPLE_NAME__", esc(os.path.basename(EXAMPLE_DAG)))
           .replace("__N_TEAMS__", str(len(TEAMS)))
           .replace("__BLOB__", REPO_BLOB)
           .replace("__UPDATED__", esc(updated)))

    with open(args.out, "w", encoding="utf-8") as fh:
        fh.write(out)
    print(f"wrote {args.out}")
    print(f"  {' + '.join(f'{t} {n}' for t, n in zip(names, totals))} "
          f"= {all_rows} epics")
    if pending:
        print(f"  {len(pending)} team(s) registered but not yet onboarded: "
              + ", ".join(pending))


if __name__ == "__main__":
    main()
