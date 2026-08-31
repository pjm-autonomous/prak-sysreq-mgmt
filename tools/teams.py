#!/usr/bin/env python3
"""The team registry: one definition per tracker, shared by every generator.

build_dependency_dag.py, build_index.py and export_snapshot.py all read this, so
a sheet id, title, or output path is stated once. Adding a team means adding one
entry here and nothing else - the per-team directories under data/ and
agile-planning/ are derived from the slug.

Layout each entry implies:

    data/<slug>/tracker-snapshot.csv          committed snapshot (source)
    agile-planning/<slug>/dependency-dag.*    generated viewer + mermaid source
    agile-planning/<slug>/standingagenda.*    the team's standing meeting agenda

A team with sheet_id None is registered but not yet onboarded: its container
exists, WORKFLOW.md steps 12-14 have not run, and there is no snapshot to build
from. The generators say so plainly rather than failing on a missing file.

Run this module directly to print the registry.
"""
from __future__ import annotations

import os

_HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(_HERE, ".."))

# Shared across every team - the capability layer is the only thing the trackers
# have in common, so it does not live in any one team's container.
SHARED_DIR = "data/shared"
CAPABILITY_META = f"{SHARED_DIR}/capability-meta.json"
CAPABILITY_JIRA = f"{SHARED_DIR}/capability-jira.json"


def _paths(slug: str, basename: str = "dependency-dag") -> dict:
    """Every path a team owns, derived from its slug. Nothing per-team is
    spelled out twice, so a new entry cannot half-adopt the layout."""
    return {
        "snapshot": f"data/{slug}/tracker-snapshot.csv",
        "outdir": f"agile-planning/{slug}",
        "basename": basename,
        "agenda": f"agile-planning/{slug}/standingagenda.html",
    }


TEAMS: dict[str, dict] = {
    "embedded": {
        **_paths("embedded"),
        "name": "Embedded-Core",
        "title": "Embedded-Core Epic Dependency DAG",
        "jira": "VSP-Embedded, project MCHTRNCS",
        # Tracker of record moved 2026-08-31 to the sheet David Hayes owns, so
        # the team maintains one sheet rather than two. It carries the same 87
        # epics plus 187 story rows indented beneath them - the generators read
        # epics only, see load_live's parentId guard.
        #
        # We hold EDITOR on it, not ADMIN: cell values are writable, column
        # structure is not. Two changes are pending with him - the Epic Total
        # column formula (points are not days) and the Blocking Epics ->
        # Blocking Issues rename, which COLUMN_ALIASES covers meanwhile.
        #
        # Previous ids: 8066207570677636 (pre-reconfiguration), and
        # 5240263122308996, now renamed archived-prak-embedded-core-epics
        # and moved to an archive folder. That sheet is the basis for the
        # simplified template the remaining teams onboard from.
        "sheet_id": 7348278000570244,
        "sheet_url": ("https://app.smartsheet.com/sheets/"
                      "VH9Xph6WX472HPP699HWXHg9hRGFXXh88w5j3Jq1"),
        "refresh": True,     # has a live tracker the scheduled job can read
    },
    "electronics": {
        **_paths("electronics"),
        "name": "Electronics",
        "title": "Electronics Epic Dependency DAG",
        "jira": "Electrical Platform, project ET",
        # Re-created 2026-08-27 with the Embedded tracker; old id
        # 5660443916849028.
        "sheet_id": 2558444740497284,
        "sheet_url": ("https://app.smartsheet.com/sheets/"
                      "f8xHmwRmFc62R5QCVM6p9ffMrVrrgJm64FMrp8x1"),
        "refresh": True,
    },
    # --- Registered, container created, not yet onboarded --------------------
    # No Smartsheet tracker and no PRAK epics in Jira yet. WORKFLOW.md steps
    # 1-11 decompose the scope, 12-14 stand up the tracker and connect it; fill
    # in sheet_id / sheet_url and flip refresh to True at that point.
    "odoa": {
        **_paths("odoa"),
        "name": "ODOA",
        "title": "ODOA Epic Dependency DAG",
        "jira": "ODOA Platform, project ODOA",
        "sheet_id": None,
        "sheet_url": "",
        "refresh": False,
    },
    "gnc": {
        **_paths("gnc"),
        "name": "GNC",
        "title": "GNC Epic Dependency DAG",
        "jira": "GNC Platform, project GNC",
        "sheet_id": None,
        "sheet_url": "",
        "refresh": False,
    },
    "mobius": {
        **_paths("mobius"),
        "name": "Mobius",
        "title": "Mobius Epic Dependency DAG",
        "jira": "Mobius Platform, project MP",
        "sheet_id": None,
        "sheet_url": "",
        "refresh": False,
    },
}

# The illustrative render. Registered so it builds like any other team rather
# than through a long ad-hoc command line, but kept out of ORDER so it never
# reaches the landing page, the capability totals, or cross-tracker resolution.
EXAMPLE = "example"
TEAMS[EXAMPLE] = {
    **_paths(EXAMPLE, basename="dependency-dag.example"),
    "name": "Example",
    "title": "Example Epic Dependency DAG",
    "jira": "illustrative only",
    "sheet_id": None,
    "sheet_url": "",
    "refresh": False,
    "note": ("ILLUSTRATIVE EXAMPLE - the edges below are sample dependencies, "
             "not real tracker data. Shown to demonstrate how a populated DAG "
             "renders."),
}

# Real teams, in landing-page order. The example is deliberately absent.
ORDER = ["embedded", "electronics", "odoa", "gnc", "mobius"]

# Everything --team accepts, including the example.
ALL = ORDER + [EXAMPLE]


def team(slug: str) -> dict:
    if slug not in TEAMS:
        raise KeyError(f"unknown team {slug!r}; known: {', '.join(ALL)}")
    return TEAMS[slug]


def onboarded(cfg: dict) -> bool:
    """True once the team has a tracker of record to read. Registered-but-not-
    onboarded teams have a container and a Jira project and nothing else."""
    return cfg["sheet_id"] is not None


def has_snapshot(cfg: dict) -> bool:
    return os.path.isfile(abspath(cfg["snapshot"]))


def others(slug: str) -> list[dict]:
    """Every other real team, for cross-tracker blocker resolution. The example
    is excluded in both directions: it never resolves against real trackers and
    real trackers never resolve against it."""
    if slug == EXAMPLE:
        return []
    return [TEAMS[s] for s in ORDER if s != slug]


def refreshable() -> list[str]:
    """Slugs the scheduled job can pull from Smartsheet."""
    return [s for s in ORDER if TEAMS[s]["refresh"]]


def abspath(rel: str) -> str:
    return os.path.normpath(os.path.join(ROOT, rel))


def _cli() -> None:
    """Print slugs for shell loops, so CI never hardcodes a team list."""
    import sys
    # Force LF. On Windows, text-mode stdout translates newlines to CRLF,
    # and a shell loop like `for t in $(teams.py --all)` then yields a
    # trailing CR on each slug, which argparse rejects as an invalid
    # choice - so the documented rebuild loop silently skips teams on the
    # very platform it gets run from by hand.
    try:
        sys.stdout.reconfigure(newline="\n")
    except AttributeError:      # pragma: no cover - Python < 3.7
        pass
    flag = sys.argv[1] if len(sys.argv) > 1 else ""
    if flag == "--refreshable":       # teams the scheduled job can pull
        print("\n".join(refreshable()))
    elif flag == "--teams":           # every real team, landing-page order
        print("\n".join(ORDER))
    elif flag == "--all":             # real teams plus the example render
        print("\n".join(ALL))
    else:
        _table()


def _table() -> None:
    for slug in ALL:
        cfg = TEAMS[slug]
        state = ("onboarded" if onboarded(cfg)
                 else "example" if slug == EXAMPLE else "not onboarded")
        sheet = cfg["sheet_id"] if onboarded(cfg) else "-"
        print(f"{slug:12} {cfg['name']:14} {state:14} sheet={sheet:<18} "
              f"{cfg['snapshot']}")


if __name__ == "__main__":
    _cli()
