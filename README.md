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
| `dependency-dag.html` | Viewer — open in a browser. Loads mermaid from a CDN, so first render needs network |
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

## Open work

See [TODO.md](TODO.md). Next scope: the Electronics epic dependency DAG.
