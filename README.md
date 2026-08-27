# prak-sysreq-mgmt

PRAK System Requirements (Jira Epics) decomposed.

The end-to-end SE process this repo sits in is documented in
[WORKFLOW.md](WORKFLOW.md), with reusable prompts in
[prompts/kickoff.md](prompts/kickoff.md).

**Contributing?** Only the repo owner has write access. Which route to use —
edit your Smartsheet tracker, or fork and open a PR — depends on what you are
changing: see [Who changes what](WORKFLOW.md#who-changes-what-access-model).
Do not hand-edit a tracker snapshot; the scheduled refresh overwrites it.

## Embedded-Core Epic Dependency DAG

A dependency graph of the 87 Embedded-Core (VSP-Embedded) PRAK epics, generated
**from the live Smartsheet tracker** so it re-populates whenever the sheet
changes. Nothing here is hand-drawn — re-run the generator and the diagram
reflects current sheet state.

- **Tracker (source of truth):** [Embedded-Core Epic Decomposition Tracker](https://app.smartsheet.com/sheets/gjWCc9QwjFV5qw57vcMf9f9rc4qmXMJvVPrx6VQ1)
- **Generator:** [`tools/build_dependency_dag.py`](tools/build_dependency_dag.py)
- **Artifacts:** [`agile-planning/embedded/`](agile-planning/embedded/)

### Files

| File | What it is |
| ------ | ------------ |
| [`agile-planning/embedded/dependency-dag.mmd`](agile-planning/embedded/dependency-dag.mmd) | Mermaid source, current sheet state (paste into Jama / GitHub / [mermaid.live](https://mermaid.live)) |
| [`agile-planning/embedded/dependency-dag.html`](agile-planning/embedded/dependency-dag.html) | Viewer — open in a browser. Loads mermaid from `vendor/`, so no network needed |
| [`agile-planning/example/dependency-dag.example.*`](agile-planning/example/) | **Illustrative** render with sample edges, to show how a fully populated DAG looks (not real dependencies) |

> Most rows still have an empty **Blocking Epics** column, so the real DAG is
> mostly unblocked epics until the evaluation meetings fill it in. The
> `.example.*` files show the intended end state.

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
`data/shared/capability-meta.json`, so a checkout without that repo still renders labels
instead of bare slugs — and says on stderr that it did.

That frontmatter is also where each capability's **Jira Initiative key** comes
from (`jira-key: MCHTRNCS-259`), so `prak-v-model` is the single source of record
for a capability's id, title, priority, and Jira identity. Nothing about a
capability is hand-maintained in this repo; `capability-meta.json` is a
write-through cache, not an input.

All 87 epics are mapped to one of 9 capabilities; there is no unassigned group.

### How it reads the sheet

Each edge comes from the tracker's **Blocking Epics** column. For a given epic,
list the epics that must progress first, comma/newline/semicolon separated;
each token is an epic id (`epic-<slug>`) or a Jira key (`MCHTRNCS-###`),
optionally tagged `(hard)` or `(soft)`:

```text
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

Dependency graph of the 15 Electronics (`ET-*`) PRAK epics, generated from the
live Smartsheet tracker so it re-populates whenever the sheet changes.

- **Tracker (source of truth):** [Electronics Epic Decomposition Tracker](https://app.smartsheet.com/sheets/JXr3hJVXxXPm6HxWWQQ845G2568xRcG35vJHRJ31)
- **Generator:** `tools/build_dependency_dag.py --team electronics`
- **Artifacts:** [`agile-planning/electronics/`](agile-planning/electronics/)

### Source

Project **ET**, label **PRAK**, team **Electrical Platform** (`ET-2951`–`ET-2965`).
Each epic is parented to a Mechatronics Initiative (`MCHTRNCS-###`); nodes group
by **Capability**, fill by **Baseline Priority**, take a bold border when
2TS = Yes, and link to their **ET** Jira epic.

Electronics epics live in `ET`, not `MCHTRNCS` — the Embedded project. A Jira
search scoped to `MCHTRNCS` will not find them.

15 epics across 4 of the 9 capabilities:

| Capability | Epics | Priority mix |
| ------------ | ------- | -------------- |
| CAP-01 Motion Authorization | 5 | 3 Must, 2 Should |
| CAP-03 Path Execution and Objectives Translation | 2 | 2 Should |
| CAP-08 Tele-operation | 7 | 4 Must, 3 Should |
| CAP-09 Observable Runtime State | 1 | 1 Must |

### Dependencies

Edges come from the **Blocking Epics** column — `(hard)` solid, `(soft)` dashed,
untagged defaults to hard. An entry may carry a comma-separated qualifier list
and a provisional marker:

```text
epic-validate-supplied-path (Embedded, soft) [guess]
epic-publish-motion-authorization-state (ET-2952, soft) [guess]
```

- The qualifier list is parsed as a set: `hard`/`soft` set edge strength, and
  anything else (`Embedded`, `ET-2952`) is a **hint** about where the blocker
  lives. Hints are used to label the node, never to resolve it.
- **`[guess]`** marks the dependency provisional — a working assumption not yet
  confirmed in an evaluation meeting. Those edges are labelled **guess** in the
  diagram and counted separately in the header.

**Cross-team blockers** (an Embedded `epic-…`) do not resolve inside the
Electronics sheet. They are **not dropped**: each becomes an **external node**,
drawn as a dashed slanted box grouped under *other tracker*, and excluded from
this team's epic count, capability tiles, and inventory — it is not Electronics
work to deliver. When the other team's snapshot is available (the `--team` preset
passes it automatically) the external node shows that epic's real title and links
to its `MCHTRNCS` Jira issue. It is not linked to the Embedded *tracker*.

Current state: **9 dependencies, 1 hard + 8 soft, all 9 provisional**, pulling in
7 distinct external Embedded blockers.

### Refresh

```bash
export SMARTSHEET_ACCESS_TOKEN=...
python3 tools/build_dependency_dag.py --team electronics --live
```

> **`--live` is currently unavailable.** The Smartsheet permission level in use
> excludes API keys; an IT request is open. Until a token exists, refresh from a
> CSV export instead — File > Export > Export to CSV in Smartsheet, then:
>
> ```bash
> python3 tools/build_dependency_dag.py --team electronics --csv path/to/export.csv
> python3 tools/build_index.py
> ```
>
> Commit the refreshed snapshot and the site updates itself; see
> [TODO.md](TODO.md).

## Teams and presets

Every team is registered in [`tools/teams.py`](tools/teams.py), so a sheet id,
URL, title, or path is stated exactly once and every generator reads the same
entry. Each team owns a container, and both paths are derived from its slug:

```
data/<slug>/tracker-snapshot.csv        source - refreshed from the sheet
agile-planning/<slug>/dependency-dag.*  generated viewer + mermaid source
agile-planning/<slug>/standingagenda.*  that team's standing meeting agenda
```

| Team | Preset | Sheet id | Jira |
| ------ | -------- | ---------- | ------ |
| Embedded-Core | `--team embedded` | `8066207570677636` | project `MCHTRNCS`, VSP-Embedded |
| Electronics | `--team electronics` | `5660443916849028` | project `ET`, Electrical Platform |
| ODOA | `--team odoa` | — not onboarded | project `ODOA`, ODOA Platform |
| GNC | `--team gnc` | — not onboarded | project `GNC`, GNC Platform |
| Mobius | `--team mobius` | — not onboarded | project `MP`, Mobius Platform |
| _(example render)_ | `--team example` | — | illustrative only |

A team with no sheet id is **registered but not onboarded**: its container and
Jira project exist, but the decomposition and the tracker do not. The generators
print a note and skip it, so a loop over every team keeps going. Onboarding one
means setting `sheet_id`, `sheet_url`, and `refresh: True` in that entry — no
other file changes.

`--team` is a preset, not a mode: it fills the sheet id, sheet URL, page title,
output directory, output basename, note, offline snapshot, and the *other* teams'
snapshots for cross-tracker blocker labels. Any flag you pass explicitly wins
over the preset.

```bash
python3 tools/build_dependency_dag.py --team electronics          # offline, from the snapshot
python3 tools/build_dependency_dag.py --team electronics --live    # from the sheet
python3 tools/export_snapshot.py --team electronics                # refresh the snapshot

python3 tools/teams.py                 # print the registry
python3 tools/teams.py --refreshable   # slugs the scheduled job pulls
python3 tools/teams.py --all           # every slug, example included
```

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
| ------ | ----------- |
| `auto` (default) | `vendor` when the bundle exists, else `cdn` |
| `vendor` | Reference the committed bundle by relative path. No CDN, no per-file weight. |
| `inline` | Embed the bundle for a single portable file. Adds ~3.5 MB per output. |
| `cdn` | Load from jsdelivr at view time. Needs network. |

`vendor` is the default in practice because the bundle is committed. It keeps the
3.5 MB out of every regenerated HTML, which matters since these files rebuild
after every meeting and would otherwise churn git history.

For the full release workflow across all three surfaces - the Pages site, a
self-contained single file to email or share, and a claude.ai Artifact - see
[PUBLISHING.md](PUBLISHING.md). The short version: anything that leaves the site
must be built with `--mermaid inline`, or its graph renders blank once the sibling
bundle and the CDN are both out of reach.

## Automated refresh

`.github/workflows/refresh-dag.yml` runs 07:00 UTC on weekdays, and on demand
from the Actions tab. For **both** teams it refreshes the snapshot from the live
sheet, rebuilds the DAG, then rebuilds the landing page, and commits only if
something changed.

Snapshots are refreshed before the DAGs are built, and the DAGs are then built
offline from those snapshots, so the diagram and the progress percentages always
describe the same read of each sheet.

> **Not yet committed.** The file exists locally but GitHub refused the push:
> creating anything under `.github/workflows/` needs the `workflow` OAuth scope,
> and the current token has only `gist`, `read:org`, `repo`. Run
> `gh auth refresh -s workflow`, then commit that file. See [TODO.md](TODO.md).

It also needs one secret once committed: `SMARTSHEET_ACCESS_TOKEN`, under
Settings > Secrets and variables > Actions. The workflow fails with a clear
message if it is missing.

## Meeting agendas

One standing agenda per team, inside that team's container as
`agile-planning/<slug>/standingagenda.*`:

| File | Meeting |
| ------ | --------- |
| [`agile-planning/embedded/standingagenda.*`](agile-planning/embedded/) | Embedded-Core, 87 epics, ~10 per session |
| [`agile-planning/electronics/standingagenda.*`](agile-planning/electronics/) | Electronics, 15 epics, ~8 per session, roles still TBD |

ODOA, GNC, and Mobius have containers but no agenda yet — they have not been
onboarded.

## Open work

See [TODO.md](TODO.md).
