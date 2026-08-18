#!/usr/bin/env python3
"""Write the committed tracker snapshot from the live Smartsheet tracker.

The snapshot in data/ exists so the build is reproducible without a Smartsheet
token, and so build_index.py can count decomposition progress. It has to be
refreshed alongside the DAG: build_index.py reads the snapshot, not the sheet, so
a stale snapshot means the landing page keeps reporting 0% progress no matter what
the meetings recorded.

Only the seven columns the generators read are written. The sheet has sixteen; the
rest are meeting scratch space (Batch, 2TS Rank, Story Titles, Owner, ...) and are
deliberately left out - this repo is public and the snapshot is committed.

Requires SMARTSHEET_ACCESS_TOKEN. Standard library only.
"""
from __future__ import annotations

import argparse
import csv
import os
import sys

# Reuse the API client and column contract rather than restating them.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_dependency_dag import COLS, DEFAULT_SHEET_ID, load_live  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sheet-id", type=int, default=DEFAULT_SHEET_ID)
    ap.add_argument("--out", required=True, help="CSV path to write")
    args = ap.parse_args()

    records = [r for r in load_live(args.sheet_id) if r["Epic"].strip()]
    if not records:
        sys.exit("ERROR: the tracker returned no rows with an Epic id; "
                 "refusing to overwrite the snapshot with an empty file.")

    records.sort(key=lambda r: r["Epic"].strip())
    os.makedirs(os.path.dirname(os.path.abspath(args.out)) or ".", exist_ok=True)
    with open(args.out, "w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=COLS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(records)

    blocked = sum(1 for r in records if r["Blocking Epics"].strip())
    evaluated = sum(1 for r in records
                    if r["2TS Required"].strip() not in ("", "TBD"))
    print(f"wrote {args.out}")
    print(f"  {len(records)} epics, {evaluated} evaluated, "
          f"{blocked} with dependencies recorded")


if __name__ == "__main__":
    main()
