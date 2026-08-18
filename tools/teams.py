#!/usr/bin/env python3
"""The team registry: one definition per tracker, shared by every generator.

Both build_dependency_dag.py (via --team) and build_index.py read this, so a
sheet id, title, or output path is stated once. Adding a third team means adding
one entry here and nothing else.

Run this module directly to print the registry.
"""
from __future__ import annotations

import os

_HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(_HERE, ".."))

TEAMS: dict[str, dict] = {
    "embedded": {
        "name": "Embedded-Core",
        "title": "Embedded-Core Epic Dependency DAG",
        "jira": "VSP-Embedded, project MCHTRNCS",
        "sheet_id": 8066207570677636,
        "sheet_url": ("https://app.smartsheet.com/sheets/"
                      "gjWCc9QwjFV5qw57vcMf9f9rc4qmXMJvVPrx6VQ1"),
        "snapshot": "data/tracker-snapshot.csv",
        "outdir": "agile-planning/dependency-dag",
        "agenda": "agile-planning/meeting-agenda/standingagenda-embedded.html",
        "refresh": True,     # has a live tracker the scheduled job can read
    },
    "electronics": {
        "name": "Electronics",
        "title": "Electronics Epic Dependency DAG",
        "jira": "Electrical Platform, project ET",
        "sheet_id": 5660443916849028,
        "sheet_url": ("https://app.smartsheet.com/sheets/"
                      "JXr3hJVXxXPm6HxWWQQ845G2568xRcG35vJHRJ31"),
        "snapshot": "data/tracker-snapshot-electronics.csv",
        "outdir": "agile-planning/dependency-dag-electronics",
        "agenda": "agile-planning/meeting-agenda/standingagenda-electronics.html",
        "refresh": True,
    },
}

ORDER = ["embedded", "electronics"]


def team(slug: str) -> dict:
    if slug not in TEAMS:
        raise KeyError(f"unknown team {slug!r}; known: {', '.join(ORDER)}")
    return TEAMS[slug]


def others(slug: str) -> list[dict]:
    """Every other team, for cross-tracker blocker resolution."""
    return [TEAMS[s] for s in ORDER if s != slug]


def abspath(rel: str) -> str:
    return os.path.normpath(os.path.join(ROOT, rel))


if __name__ == "__main__":
    for slug in ORDER:
        cfg = TEAMS[slug]
        print(f"{slug:12} {cfg['name']:14} sheet={cfg['sheet_id']}  "
              f"{cfg['snapshot']}")
