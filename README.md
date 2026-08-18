# prak-sysreq-mgmt

PRAK System Requirements (Jira Epics) decomposed.

## Embedded-Core Epic Dependency DAG

A dependency graph of the 87 Embedded-Core (VSP-Embedded) PRAK epics, generated
**from the live Smartsheet tracker** so it re-populates whenever the sheet
changes. Nothing here is hand-drawn — re-run the generator and the diagram
reflects current sheet state.

- **Tracker (source of truth):** [Embedded-Core Epic Decomposition Tracker](https://app.smartsheet.com/sheets/gjWCc9QwjFV5qw57vcMf9f9rc4qmXMJvVPrx6VQ1)
- **Generator:** [`tools/build_dependency_dag.py`](tools/build_dependency_dag.py)

### Files

| File | What it is |
|------|------------|
| `dependency-dag.mmd` | Mermaid source, current sheet state (paste into Jama / GitHub / [mermaid.live](https://mermaid.live)) |
| `dependency-dag.html` | Viewer — open in a browser. Loads mermaid from `vendor/`, so no network needed |
| `dependency-dag.example.*` | **Illustrative** render with sample edges, to show how a populated DAG looks (not real dependencies) |

> The current `dependency-dag.*` has **0 edges** until the evaluation meetings
> fill in the tracker's **Blocking Epics** column. The `.example.*` files show
> the intended result.

### Reading the viewer

Two sections, in this order:

1. **Dependency graph** — one zoomable, pannable panel per dependency chain.
   Empty state until `Blocking Epics` is filled in.
2. **Epic inventory** — a two-level drill-down, because 87 epic cards on one
   screen is a wall of rows nobody reads:
   - **Level 1:** one clickable tile per **PRD capability**, labelled with its
     `CAP-nn` id, its title, epic count, priority mix, and 2TS count. Tiles are
     ordered by PRD id. The drilled-in view is linkable
     (`...html#cap=motion-authorization`), and browser Back works.
   - **Level 2:** that capability's epics as cards, full untruncated titles,
     each linking to its Jira epic.
   - **Search or any filter** cuts across every capability at once and steps
     the tiles aside; Reset returns to level 1.

The tracker's **Capability** column holds a capreq slug, so each value resolves
straight to `product/requirements/product/capreq-<slug>.md` in the `prak-v-model`
checkout named by `--vmodel` (default `../prak-v-model`), which supplies the
`CAP-nn` id and the title. The resolved map is cached to
`data/capability-meta.json`, so a checkout without that repo still renders labels
instead of bare slugs.

All 87 epics are mapped to one of 9 capabilities; there is no unassigned group.

### How it reads the sheet

Each edge comes from the tracker's **Blocking Epics** column. For a given epic,
list the epics that must progress first, comma/newline/semicolon separated;
each token is an epic id (`epic-<slug>`) or a Jira key (`MCHTRNCS-###`),
optionally tagged `(hard)` or `(soft)`:

```
epic-subscribe-all-stop-broadcaster (hard), MCHTRNCS-220 (soft)
```

- **hard** — can't start until the blocker is done → solid arrow `-->`
- **soft** — can start, can't finish until the blocker is done → dashed arrow `-.->`
- untagged defaults to **hard**. Edge direction is **blocker → dependent**.

Nodes are grouped by **Capability**, filled by **Baseline Priority**
(Must / Should / Could), and drawn with a **bold border when 2TS Required = Yes**.
Each node links to its Jira epic.

### Refreshing (make it "live")

Re-run whenever the sheet changes. Two data sources:

```bash
# Live pull over the Smartsheet API (hands-off, scriptable/CI):
export SMARTSHEET_ACCESS_TOKEN=...   # Smartsheet > Personal Settings > API Access
python3 tools/build_dependency_dag.py --live

# Offline from a CSV export (File > Export > Export to CSV):
python3 tools/build_dependency_dag.py --csv path/to/export.csv
```

For automatic refresh, run `--live` on a schedule — a cron job, a CI workflow
(e.g. after each meeting day), or a Smartsheet-triggered webhook. The token is
the only secret required.

## Electronics Epic Dependency DAG

The Electronics-team counterpart, tracked **separately** from Embedded-Core. The
two teams share parent PRD Capability Requirements but no epics: of the 15
Electronics epics, zero appear in the 87-row Embedded-Core tracker.

- **Source (for now):** `prak-v-model/agile-planning/epics/`, the 15 epics with
  `platform-team: Electronics`. There is no Electronics Smartsheet tracker yet, so
  unlike Embedded-Core this DAG is generated from the v-model repo rather than
  from a live sheet.
- **Snapshot:** [`data/tracker-snapshot-electronics.csv`](data/tracker-snapshot-electronics.csv)
- **Artifacts:** [`agile-planning/dependency-dag-electronics/`](agile-planning/dependency-dag-electronics/)

15 epics across 4 capabilities:

| Capability | Epics | Priority mix |
|------------|-------|--------------|
| CAP-01 Motion Authorization | 5 | 3 Must, 2 Should |
| CAP-03 Path Execution and Objectives Translation | 2 | 2 Should |
| CAP-08 Tele-operation | 7 | 4 Must, 3 Should |
| CAP-09 Observable Runtime State | 1 | 1 Must |

**Jira keys** are the `ET` project epics `ET-2951`..`ET-2965` (Electrical Team).
Electronics epics live in `ET`, not `MCHTRNCS` — the Embedded epics' project — so
a search scoped to `MCHTRNCS` will not find them.

Each epic's Jira parent independently confirms its capability: all 15 agree with
the capability resolved through `prak-v-model`, zero disagreements.

### Regenerating

```bash
python3 tools/build_dependency_dag.py   --csv data/tracker-snapshot-electronics.csv   --outdir agile-planning/dependency-dag-electronics   --basename dependency-dag   --title "Electronics Epic Dependency DAG"   --sheet-url ""
```

Rebuild the snapshot from `prak-v-model` whenever its Electronics epics change,
then refill the `Jira Key` column from a Jira export of the `ET` project.
Once an Electronics tracker sheet exists, swap `--csv` for `--live --sheet-id
<id> --sheet-url <url>`; no other change is needed.

## Published site

[`index.html`](index.html) is the landing page: one card per team with links to
that team's DAG, mermaid source, agenda, and tracker, plus the shared capability
table. Every number on it is counted from the committed snapshots, so it cannot
drift from the DAGs beside it.

```bash
python3 tools/build_index.py      # run after regenerating any DAG
```

GitHub Pages should serve from **`main`, root**. Publishing from `/docs` or a
`gh-pages` branch would mean copying build products to a second location on every
regeneration, which silently goes stale; root has no such step. Everything in the
repo is web-reachable that way, which is already true of a public repo.

Mermaid is committed at [`vendor/mermaid.min.js`](vendor/mermaid.min.js) (11.16.1,
UMD) so no page depends on a CDN at view time. The generator's `--mermaid` flag
selects how it is loaded:

| Mode | Behaviour |
|------|-----------|
| `auto` (default) | `vendor` when the bundle exists, else `cdn` |
| `vendor` | Reference the committed bundle by relative path. No CDN, no per-file weight. |
| `inline` | Embed the bundle for a single portable file. Adds ~3.5 MB per output. |
| `cdn` | Load from jsdelivr at view time. Needs network. |

`vendor` is the default in practice because the bundle is committed. It keeps the
3.5 MB out of every regenerated HTML, which matters since these files rebuild
after every meeting and would otherwise churn git history.

## Automated refresh

`.github/workflows/refresh-dag.yml` runs 07:00 UTC on weekdays, and on demand
from the Actions tab. It re-reads the Embedded-Core tracker, refreshes
`data/tracker-snapshot.csv`, rebuilds the DAG and landing page, and commits only
if something changed. Electronics is not refreshed, having no tracker yet.

> **Not yet committed.** The file exists locally but GitHub refused the push:
> creating anything under `.github/workflows/` needs the `workflow` OAuth scope,
> and the current token has only `gist`, `read:org`, `repo`. Run
> `gh auth refresh -s workflow`, then commit that file. See [TODO.md](TODO.md).

It also needs one secret once committed: `SMARTSHEET_ACCESS_TOKEN`, under
Settings > Secrets and variables > Actions. The workflow fails with a clear
message if it is missing.

## Meeting agendas

One standing agenda per team, in
[`agile-planning/meeting-agenda/`](agile-planning/meeting-agenda/):

| File | Meeting |
|------|---------|
| `standingagenda-embedded.*` | Embedded-Core, 87 epics, ~10 per session |
| `standingagenda-electronics.*` | Electronics, 15 epics, ~8 per session, roles still TBD |

## Open work

See [TODO.md](TODO.md).
