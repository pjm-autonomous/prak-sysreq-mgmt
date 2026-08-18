# prak-sysreq-mgmt

PRAK System Requirements (Jira epics) decomposed into dependency DAGs and
decomposition-progress views, generated from the trackers of record.

## What this repo is

Two teams' PRAK epics, tracked separately, sharing one capability layer:

| Team | Epics | Jira | Tracker of record | Preset |
|------|------:|------|-------------------|--------|
| Embedded-Core | 87 | project `MCHTRNCS`, team VSP-Embedded | Smartsheet `8066207570677636` | `--team embedded` |
| Electronics | 15 | project `ET`, team Electrical Platform | Smartsheet `5660443916849028` | `--team electronics` |

Both are registered in `tools/teams.py`. **That is the only place a sheet id, URL,
title, or output path belongs** - every generator reads it. Adding a team means
adding one entry there and nothing else.

Both teams' epics hang off the same 9 PRD Capability Requirements, which are Jira
`Initiative` issues (`MCHTRNCS-259`..`-266`, `-268`). **That is the only layer the
two share - no epic appears in both trackers.** Cross-team dependency belongs at
the capability level, never in a tracker's `Blocking Epics` column, which resolves
epic ids within a single sheet only and silently drops dangling references.

## Hard rules

1. **Nothing is hand-drawn.** Every diagram and page is generated. If a number or
   a node is wrong, fix the tracker or the generator, never the output file.
2. **Regenerate, do not hand-edit,** anything under `agile-planning/*/` or
   `index.html`. They are build products and get overwritten.
3. **This repo is public.** Do not commit raw Jira or Smartsheet exports. They
   carry Atlassian account ids and, in the ECR field templates, internal labor
   rates. Commit only pruned derivatives with the columns actually used.
   `data/prak_jira_snapshot-*.csv` is gitignored for this reason.
4. **The tracker is the source of truth,** not the snapshot in `data/`. Snapshots
   are committed so the build is reproducible offline; refresh them from the sheet
   rather than editing them by hand.

## Layout

| Path | What |
|------|------|
| `tools/build_dependency_dag.py` | Tracker -> Mermaid + drill-down viewer. Stdlib only. |
| `tools/build_index.py` | Snapshots -> `index.html` landing/progress page. Stdlib only. |
| `data/tracker-snapshot.csv` | Embedded-Core, 87 rows, the 7 columns the generator reads |
| `data/tracker-snapshot-electronics.csv` | Electronics, 15 rows |
| `data/tracker-snapshot.example.csv` | Same shape with sample edges, for the example render |
| `data/capability-meta.json` | capreq slug -> `CAP-nn` + title, cached from `prak-v-model` |
| `data/capability-jira.json` | capreq slug -> Jira Initiative key |
| `vendor/mermaid.min.js` | Mermaid 11.16.1 UMD, so pages need no CDN |
| `agile-planning/dependency-dag/` | Embedded artifacts, plus the `.example.*` render |
| `agile-planning/dependency-dag-electronics/` | Electronics artifacts |
| `agile-planning/meeting-agenda/` | One standing agenda per team |
| `index.html` | Site landing page, served by GitHub Pages from `main` root |

## Rebuilding everything

```bash
export SMARTSHEET_ACCESS_TOKEN=...        # only needed for --live

# Refresh snapshots from the sheets, then build offline from them, so the
# diagrams and the progress percentages describe the same read.
python3 tools/export_snapshot.py --team embedded
python3 tools/export_snapshot.py --team electronics
python3 tools/build_dependency_dag.py --team embedded
python3 tools/build_dependency_dag.py --team electronics

# The illustrative example render
python3 tools/build_dependency_dag.py --csv data/tracker-snapshot.example.csv \
  --basename dependency-dag.example \
  --note "ILLUSTRATIVE EXAMPLE - the edges below are sample dependencies, not real tracker data. Shown to demonstrate how a populated DAG renders."

# Landing page LAST - it counts from the snapshots
python3 tools/build_index.py
```

Without a token, `--team <x>` alone builds offline from that team's committed
snapshot.

`.github/workflows/refresh-dag.yml` does the Embedded refresh on a schedule and
commits any change.

## Conventions that are easy to get wrong

- The tracker's grouping column is **`Capability`**, holding a **capreq slug**
  (the capreq filename with `capreq-` dropped). It was renamed from `Initiative`
  on 2026-08-18. The slug resolves to `capreq-<slug>.md` in `prak-v-model`.
- Electronics epics are project **`ET`**, not `MCHTRNCS`. A Jira search scoped to
  `MCHTRNCS` will not find them - this already caused one wrong conclusion.
- `Blocking Epics` direction is **blocker -> dependent**. `(hard)` means cannot
  start, `(soft)` means cannot finish; untagged defaults to hard.
- A blocker entry may carry a comma-separated qualifier list and a marker:
  `epic-x (Embedded, soft) [guess]`. Qualifiers other than hard/soft are hints
  about where the blocker lives and never affect resolution. `[guess]` marks the
  edge provisional. **Never split that cell on commas naively** - doing so tore
  entries in half and silently produced zero edges.
- A blocker that does not resolve inside the sheet is **not dropped**: it becomes
  an external node, drawn under *other tracker* and excluded from that team's
  counts, tiles, and inventory. Dropping it is what made cross-team dependencies
  invisible.
- The generator needs `prak-v-model` checked out as a **sibling directory** for
  capability titles, or it falls back to `data/capability-meta.json`, or to bare
  slugs. Override with `--vmodel`.
- Priorities are MoSCoW (`Must Have`/`Should Have`/`Could Have`/`Will Not Have`),
  pre-filled from the epic. Do not edit them in meetings.

## Current state

Both DAGs render every epic as unblocked: `Blocking Epics` is empty across all
102 rows because the evaluation meetings have not happened yet. This is expected,
not a bug. `dependency-dag.example.*` shows what a populated DAG looks like.

See [TODO.md](TODO.md) for open work.
