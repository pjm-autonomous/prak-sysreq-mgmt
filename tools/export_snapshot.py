#!/usr/bin/env python3
"""Write the committed tracker snapshot from a tracker.

Two sources, same output: --live pulls over the Smartsheet API, --from-csv reads
a Grid CSV exported by hand (File > Export > Export to CSV). The offline route
exists because the API token is not available yet, and it has to produce a
byte-identical snapshot to the live route - same columns, same sort - or the
committed viewer churns every time the refresh alternates between them.

The snapshot in data/<team>/ exists so the build is reproducible without a Smartsheet
token, and so build_index.py can count decomposition progress. It has to be
refreshed alongside the DAG: build_index.py reads the snapshot, not the sheet, so
a stale snapshot means the landing page keeps reporting 0% progress no matter what
the meetings recorded.

Only the columns the generators read are written: the 7 required ones plus
Eval Status, which drives a visual indicator and is tolerated when absent. The
sheet has sixteen; the rest are meeting scratch space (Batch, 2TS Rank, Story
Titles, Owner, ...) and are deliberately left out - this repo is public and the
snapshot is committed.

--live requires SMARTSHEET_ACCESS_TOKEN; --from-csv requires nothing.
Standard library only.
"""
from __future__ import annotations

import argparse
import csv
import os
import sys

# Reuse the API client and column contract rather than restating them.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import teams as team_registry  # noqa: E402
from build_dependency_dag import (  # noqa: E402
    ALL_COLS,
    DEFAULT_SHEET_ID,
    load_csv,
    load_live,
)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--team", choices=team_registry.ORDER,
                    help="preset from tools/teams.py: fills --sheet-id and --out")
    ap.add_argument("--sheet-id", type=int, default=DEFAULT_SHEET_ID)
    ap.add_argument("--out", help="CSV path to write")
    ap.add_argument("--from-csv", metavar="PATH",
                    help="read a Grid CSV export instead of the live API. The "
                         "export keeps every sheet column; only the 7 the "
                         "generators read are written out, so no raw export "
                         "reaches this public repo.")
    args = ap.parse_args()

    if args.team:
        cfg = team_registry.team(args.team)
        # A team with no sheet id has no tracker of record to pull from. An
        # explicit --from-csv is still fine: the caller has the rows in hand.
        if not team_registry.onboarded(cfg) and not args.from_csv:
            print(f"{cfg['name']}: not onboarded - no Smartsheet tracker to "
                  f"export. Stand one up first (WORKFLOW.md steps 12-14) and "
                  f"set sheet_id in tools/teams.py, or pass --from-csv PATH.")
            return
        if args.sheet_id == DEFAULT_SHEET_ID and cfg["sheet_id"] is not None:
            args.sheet_id = cfg["sheet_id"]
        if not args.out:
            args.out = team_registry.abspath(cfg["snapshot"])
    if not args.out:
        ap.error("pass --out PATH or --team")

    if args.from_csv:
        source = args.from_csv
        rows = load_csv(args.from_csv)
    else:
        source = f"sheet {args.sheet_id}"
        rows = load_live(args.sheet_id)
    records = [r for r in rows if r["Epic"].strip()]
    if not records:
        sys.exit(f"ERROR: {source} returned no rows with an Epic id; "
                 "refusing to overwrite the snapshot with an empty file.")

    records.sort(key=lambda r: r["Epic"].strip())
    os.makedirs(os.path.dirname(os.path.abspath(args.out)) or ".", exist_ok=True)
    # newline="" hands newline control to csv, and lineterminator pins it to
    # LF so the file is byte-identical whoever ran it. csv defaults to CRLF,
    # which a Windows checkout normalises away on commit and a Linux CI runner
    # does not - leaving the two rewriting each other's snapshots forever.
    with open(args.out, "w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=ALL_COLS, extrasaction="ignore",
                                lineterminator="\n")
        writer.writeheader()
        writer.writerows(records)

    blocked = sum(1 for r in records if r["Blocking Epics"].strip())
    evaluated = sum(1 for r in records
                    if r["2TS Required"].strip() not in ("", "TBD"))
    print(f"wrote {args.out}  (from {source})")
    print(f"  {len(records)} epics, {evaluated} evaluated, "
          f"{blocked} with dependencies recorded")


if __name__ == "__main__":
    main()
