#!/usr/bin/env python3
"""Check a team's tracker against the contract in data/shared/tracker-schema.json.

Two kinds of problem, and the difference matters:

  ERROR   the build will be wrong, or wrong-looking. A blocker that resolves to
          nothing draws a phantom node under "other tracker" that reads exactly
          like a real cross-team dependency - that is how "Unknown" sat in the
          Embedded tracker on 2026-08-27 producing a dependency nobody had.
  WARN    drift from the schema that does not corrupt the output. A column that
          lost its dropdown still holds the right text; it just lets the next
          typo through silently.

This exists because five teams edit five trackers and only one person has repo
write. Without it, an SE's mistake reaches the published site as a plausible
diagram rather than a named problem.

Offline by default - validates the committed snapshot. --live also checks the
sheet's structure (column types, dropdown options, formulas), which a snapshot
cannot carry. Standard library only.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

import teams as team_registry  # noqa: E402
from build_dependency_dag import (  # noqa: E402
    ALL_COLS,
    capability_of,
    load_capability_meta,
    load_csv,
    load_live,
    parse_blockers,
    smartsheet_get,
)

SCHEMA_PATH = team_registry.abspath("data/shared/tracker-schema.json")


def load_schema(path: str = SCHEMA_PATH) -> dict:
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


class Report:
    """Collects findings so every problem is reported, not just the first."""

    def __init__(self, team: str) -> None:
        self.team = team
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def error(self, msg: str) -> None:
        self.errors.append(msg)

    def warn(self, msg: str) -> None:
        self.warnings.append(msg)

    @property
    def ok(self) -> bool:
        return not self.errors

    def render(self) -> str:
        out = [f"--- {self.team} ---"]
        for m in self.errors:
            out.append(f"  ERROR  {m}")
        for m in self.warnings:
            out.append(f"  warn   {m}")
        if not self.errors and not self.warnings:
            out.append("  clean")
        return "\n".join(out)


def check_rows(rows: list[dict], schema: dict, meta: dict, report: Report,
               known_epics: set[str], elsewhere: dict[str, str]) -> None:
    """Validate the data a snapshot carries."""
    required = schema["required"]
    seen_epic: dict[str, int] = {}
    seen_key: dict[str, int] = {}

    for i, row in enumerate(rows, start=2):        # +2: header is line 1
        epic = row.get("Epic", "").strip()
        if not epic:
            report.error(f"row {i}: empty Epic id")
            continue

        # Uniqueness. A duplicate silently merges two epics in every count.
        if epic in seen_epic:
            report.error(f"row {i}: duplicate Epic id {epic!r} (also row {seen_epic[epic]})")
        seen_epic[epic] = i

        for col in ("Epic", "Jira Key"):
            pattern = required.get(col, {}).get("pattern")
            value = row.get(col, "").strip()
            if pattern and value and not re.match(pattern, value):
                report.error(f"row {i}: {col} {value!r} does not match {pattern}")

        key = row.get("Jira Key", "").strip()
        if key:
            if key in seen_key:
                report.error(f"row {i}: duplicate Jira Key {key!r} "
                             f"(also row {seen_key[key]})")
            seen_key[key] = i

        # Enum columns. Checked from the snapshot because a dropdown can be
        # lost - as it was - while the values stay valid, and vice versa.
        for col, spec in {**required, **schema["optional"]}.items():
            options = spec.get("options")
            value = row.get(col, "").strip()
            if options and value and value not in options:
                report.error(f"row {i}: {col} {value!r} not one of {options}")

        # Capability must resolve, or the epic lands in "No parent capability".
        cap = capability_of(row)
        if not row.get("Capability", "").strip():
            report.warn(f"row {i}: {epic} has no Capability - it will group under "
                        f"'No parent capability'")
        elif meta and cap not in meta:
            report.error(f"row {i}: Capability {cap!r} does not resolve to a "
                         f"capreq in prak-v-model")

        # The finding that motivated this tool. Three outcomes, and the
        # distinction is the whole point: a cross-team blocker is normal and
        # must not raise anything, or the noise trains people to skip the
        # report and the one real fault goes with it.
        for ref, _kind, _prov, hint in parse_blockers(row.get("Blocking Issues", "")):
            if ref in known_epics:
                continue                          # same tracker, resolves
            if ref in elsewhere:
                continue                          # another team's epic, draws external
            if re.match(r"^[A-Z][A-Z0-9]+-[0-9]+$", ref):
                report.warn(f"row {i}: {epic} is blocked by Jira issue {ref!r}, which no "
                            f"tracker resolves - it draws as an external node with no "
                            f"title" + (f" (hint: {hint})" if hint else ""))
            else:
                report.error(f"row {i}: {epic} is blocked by {ref!r}, which is not an "
                             f"epic in any tracker and is not a Jira key. It draws a "
                             f"phantom node indistinguishable from a real cross-team "
                             f"dependency. Leave the cell empty if the blocker is not "
                             f"yet identified.")


def check_structure(sheet: dict, schema: dict, sheet_name: str,
                    report: Report) -> None:
    """Validate what only the live sheet can tell us: types, options, formulas."""
    by_title = {c["title"]: c for c in sheet["columns"]}
    aliases = schema.get("aliases", {})
    for title, old in [(v, k) for k, v in aliases.items()]:
        if title not in by_title and old in by_title:
            report.warn(f"column still named {old!r}; the schema calls it {title!r}")
            by_title[title] = by_title[old]

    for col, spec in {**schema["required"], **schema["optional"]}.items():
        column = by_title.get(col)
        if column is None:
            if col in schema["required"]:
                report.error(f"column {col!r} is missing - the tracker cannot be built")
            continue
        want_type = spec.get("type")
        if want_type and column["type"] != want_type:
            level = report.warn if want_type == "PICKLIST" else report.error
            level(f"column {col!r} is {column['type']}, schema says {want_type}"
                  + (" - a lost dropdown lets the next typo through"
                     if want_type == "PICKLIST" else ""))
        want_options = spec.get("options")
        if want_options and column["type"] == "PICKLIST":
            missing = [o for o in want_options if o not in (column.get("options") or [])]
            if missing:
                report.warn(f"column {col!r} dropdown is missing options: {missing}")

    # Hyperlinks and formulas.
    id2title = {c["id"]: c["title"] for c in sheet["columns"]}
    linked = unlinked = 0
    formula_cols: dict[str, int] = {}
    for row in sheet.get("rows", []):
        for cell in row.get("cells", []):
            title = id2title.get(cell.get("columnId"))
            if title == "Jira Key" and str(cell.get("value", "") or "").strip():
                if cell.get("hyperlink"):
                    linked += 1
                else:
                    unlinked += 1
            if cell.get("formula"):
                formula_cols[title] = formula_cols.get(title, 0) + 1
            if cell.get("errorCode") or (cell.get("error") or {}).get("code"):
                report.error(f"cell error in column {title!r}: "
                             f"{cell.get('errorCode') or cell['error'].get('code')}")
    if unlinked:
        report.warn(f"Jira Key: {unlinked} of {linked + unlinked} cells have no hyperlink")

    for col, formula in schema.get("formulas", {}).get(sheet_name, {}).items():
        have = formula_cols.get(col, 0)
        if not have:
            report.warn(f"column {col!r} has no formula; schema expects {formula}")


def validate_source(label: str, rows: list[dict], vmodel: str,
                    sheet: dict | None, cross: list[dict]) -> Report:
    """Validate rows from anywhere: a registered team, a CSV, or a raw sheet."""
    report = Report(label)
    schema = load_schema()
    rows = [r for r in rows if r.get("Epic", "").strip()]
    meta = load_capability_meta(vmodel, team_registry.abspath(
        team_registry.CAPABILITY_META))
    known = {r["Epic"].strip() for r in rows}
    elsewhere = {}
    for other in cross:
        for row in load_csv(team_registry.abspath(other["snapshot"])):
            eid = row.get("Epic", "").strip()
            if eid:
                elsewhere[eid] = other["name"]
    check_rows(rows, schema, meta, report, known, elsewhere)
    if sheet is not None:
        check_structure(sheet, schema, sheet["name"], report)
    return report


def validate_adhoc(sheet_id: int | None, csv_path: str | None,
                   vmodel: str) -> Report:
    """A sheet or CSV that is not (yet) a registered team."""
    token = os.environ.get("SMARTSHEET_ACCESS_TOKEN")
    sheet = None
    if sheet_id:
        if not token:
            sys.exit("ERROR: --sheet-id needs SMARTSHEET_ACCESS_TOKEN.")
        sheet = smartsheet_get(f"sheets/{sheet_id}", token)
        rows = load_live(sheet_id)
        label = f"sheet {sheet_id} ({sheet['name']})"
    else:
        rows = load_csv(csv_path)
        label = csv_path
    # Resolve blockers against every onboarded tracker, so a candidate sheet's
    # cross-team references are recognised rather than reported as faults.
    cross = [team_registry.team(s) for s in team_registry.ORDER
             if team_registry.has_snapshot(team_registry.team(s))]
    return validate_source(label, rows, vmodel, sheet, cross)


def validate(slug: str, live: bool, vmodel: str) -> Report:
    cfg = team_registry.team(slug)
    report = Report(f"{slug} ({cfg['name']})")
    schema = load_schema()

    if not team_registry.has_snapshot(cfg) and not live:
        report.warn("no snapshot yet - nothing to validate")
        return report

    rows = (load_live(cfg["sheet_id"]) if live
            else load_csv(team_registry.abspath(cfg["snapshot"])))
    rows = [r for r in rows if r.get("Epic", "").strip()]
    meta = load_capability_meta(vmodel, team_registry.abspath(
        team_registry.CAPABILITY_META))
    known = {r["Epic"].strip() for r in rows}
    # Every other team's epics, so a cross-tracker blocker resolves instead of
    # being reported. This mirrors what build_dependency_dag does with
    # --cross-reference; validating against one tracker alone would flag every
    # legitimate cross-team dependency as a fault.
    elsewhere: dict[str, str] = {}
    for other in team_registry.others(slug):
        if not team_registry.has_snapshot(other):
            continue
        for row in load_csv(team_registry.abspath(other["snapshot"])):
            eid = row.get("Epic", "").strip()
            if eid:
                elsewhere[eid] = other["name"]
    check_rows(rows, schema, meta, report, known, elsewhere)

    if live:
        sheet = smartsheet_get(f"sheets/{cfg['sheet_id']}",
                               os.environ["SMARTSHEET_ACCESS_TOKEN"])
        check_structure(sheet, schema, sheet["name"], report)
    return report


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--team", choices=team_registry.ORDER,
                    help="one team (default: every onboarded team)")
    ap.add_argument("--sheet-id", type=int,
                    help="validate an arbitrary Smartsheet, registered or not - "
                         "use before adopting a sheet or onboarding a team")
    ap.add_argument("--csv", metavar="PATH",
                    help="validate an arbitrary snapshot or export")
    ap.add_argument("--live", action="store_true",
                    help="also check the sheet's structure over the API")
    ap.add_argument("--vmodel", default=os.path.normpath(
        os.path.join(_HERE, "..", "..", "prak-v-model")))
    ap.add_argument("--strict", action="store_true",
                    help="exit non-zero on warnings as well as errors")
    args = ap.parse_args()

    if args.sheet_id or args.csv:
        report = validate_adhoc(args.sheet_id, args.csv, args.vmodel)
        print(report.render())
        print(f"\n{len(report.errors)} error(s), {len(report.warnings)} warning(s)")
        if report.errors or (args.strict and report.warnings):
            sys.exit(1)
        return

    slugs = [args.team] if args.team else [
        s for s in team_registry.ORDER
        if team_registry.has_snapshot(team_registry.team(s))]
    if not slugs:
        print("no onboarded teams to validate")
        return

    reports = [validate(s, args.live, args.vmodel) for s in slugs]
    print("\n".join(r.render() for r in reports))
    errors = sum(len(r.errors) for r in reports)
    warns = sum(len(r.warnings) for r in reports)
    print(f"\n{errors} error(s), {warns} warning(s) across {len(reports)} tracker(s)")
    if errors or (args.strict and warns):
        sys.exit(1)


if __name__ == "__main__":
    main()
