# prak-sysreq-mgmt

PRAK System Requirements (Jira epics) decomposed into dependency DAGs and
decomposition-progress views, generated from the trackers of record.

## What this repo is

Five technical teams' PRAK epics, tracked separately, sharing one capability
layer. Each team owns a container - `data/<slug>/` for its snapshot,
`agile-planning/<slug>/` for its generated artifacts and standing agenda.

| Team | Slug | Epics | Jira | Tracker of record |
|------|------|------:|------|-------------------|
| Embedded-Core | `embedded` | 87 | project `MCHTRNCS`, team VSP-Embedded | `Embedded-Core Epic Decomp`, sheet `7348278000570244` |
| Electronics | `electronics` | 15 | project `ET`, team Electrical Platform | `prak-electronics-epics`, sheet `2558444740497284` |
| ODOA | `odoa` | - | project `ODOA`, ODOA Platform | none yet |
| GNC | `gnc` | - | project `GNC`, GNC Platform | none yet |
| Mobius | `mobius` | - | project `MP`, Mobius Platform | none yet |

The last three are **registered but not onboarded**: the container and the Jira
project exist, the decomposition (WORKFLOW.md steps 1-11) and the tracker
(steps 12-14) do not. `sheet_id` is `None` for them, which is what every
generator keys off - they print a note and skip rather than failing. Set a real
sheet id and `refresh: True` when the tracker goes live.

**The two live trackers are not the same shape.** Embedded is hierarchical:
87 epic rows with 187 story rows indented beneath 46 of them. Electronics is
flat - 15 epic rows, no children. Both are valid; the generators read epics
only and skip child rows structurally (see the `parentId` guard in
`load_live`). ODOA, GNC and Mobius onboard from **`prak-TEMPLATE-epics`**
(sheet `4956716494966660`), built from the archived
`archived-prak-embedded-core-epics` with no rows - so expect flat trackers
there unless a team chooses to add stories. Copy it, name the copy
`prak-<slug>-epics`, and run `tools/validate_tracker.py --sheet-id <id>`
before adding the registry entry.

All are registered in `tools/teams.py`. **That is the only place a sheet id, name,
URL, title, or team path belongs** - every generator reads it, and the per-team
paths are derived from the slug. Adding a team means adding one entry there and
nothing else.

**`sheet_id` addresses; `sheet_name` asserts; `sheet_url` only decorates.** Every
API call resolves by id - a URL is never used to reach a sheet. Because an id is
opaque, `load_live` compares the name the API reports against the registry's
`sheet_name` and warns on stderr when they diverge, so a sheet renamed or an id
repointed shows up instead of reading as a clean pull. `sheet_url` exists solely
for the links on the generated pages. Rename a sheet and you must re-key two
places: `sheet_name` here, and the per-sheet block in `tracker-schema.json`
`formulas`, which is keyed by name and silently checks nothing when it is stale
(the validator now names that gap).

Smartsheet accounts: everything lives under **`c00236@contractor.asirobots.com`**.
The older `patrick.mckee-cn47@contractor.asirobots.com` is dead - see
[CREDENTIALS.md](CREDENTIALS.md).

Every team's epics hang off the same 9 PRD Capability Requirements, which are Jira
`Initiative` issues (`MCHTRNCS-259`..`-266`, `-268`). **That is the only layer the
trackers share - no epic appears in two of them.** Cross-team dependency belongs
at the capability level, never in a tracker's `Blocking Issues` column, which
resolves epic ids within a single sheet only.

## Hard rules

1. **Nothing is hand-drawn.** Every diagram and page is generated. If a number or
   a node is wrong, fix the tracker or the generator, never the output file.
2. **Regenerate, do not hand-edit,** anything under `agile-planning/*/`,
   `index.html`, or `data/shared/capability-meta.json`. They are build products
   and get overwritten. (`agile-planning/<slug>/standingagenda.*` is the one
   exception - those are authored by hand.)
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
| `tools/teams.py` | The registry. Every per-team path below is derived from a slug here. |
| `tools/validate_tracker.py` | Tracker -> findings, against the schema. `--live` also checks column types and formulas. |
| `data/shared/tracker-schema.json` | **Input, not a build product.** The contract a tracker must satisfy. |
| `CREDENTIALS.md` | What each credential reaches, where it lives, when it expires. |
| `data/<slug>/tracker-snapshot.csv` | That team's snapshot - the 7 columns the generator reads, plus optional `Eval Status` |
| `data/shared/capability-meta.json` | **Build product.** capreq slug -> `CAP-nn`, title, priority, Jira key. Regenerated from `prak-v-model`. |
| `data/shared/capability-jama.json` | **Input, not a build product.** Hand-kept capreq slug -> Jama item id, for the capability links. Delete once every capreq carries `jama-id`. |
| `data/example/tracker-snapshot.csv` | Same shape with sample edges, for the example render |
| `agile-planning/<slug>/dependency-dag.*` | That team's generated viewer + Mermaid source |
| `agile-planning/<slug>/standingagenda.*` | That team's standing meeting agenda |
| `agile-planning/example/dependency-dag.example.*` | The illustrative render |
| `vendor/mermaid.min.js` | Mermaid 11.16.1 UMD, so pages need no CDN |
| `index.html` | Site landing page, served by GitHub Pages from `main` root |

`data/shared/` is the only directory not owned by a team, because the capability
layer is the only thing the trackers have in common. Nothing in it is authored
here **except `tracker-schema.json`**, which is the one hand-written input in
that directory - see *The capability layer* below.

## Rebuilding everything

```bash
export SMARTSHEET_ACCESS_TOKEN=...        # only needed for --live

# Refresh snapshots from the sheets, then build offline from them, so the
# diagrams and the progress percentages describe the same read.
for t in $(python3 tools/teams.py --refreshable); do
  python3 tools/export_snapshot.py --team "$t"
done

# Every DAG plus the example render. Not-yet-onboarded teams print a note and
# are skipped, so this loop never needs editing when a team is added.
for t in $(python3 tools/teams.py --all); do
  python3 tools/build_dependency_dag.py --team "$t"
done

# Landing page LAST - it counts from the snapshots
python3 tools/build_index.py
```

Without a token, `--team <x>` alone builds offline from that team's committed
snapshot. `python3 tools/teams.py` prints the registry; `--teams`,
`--refreshable`, and `--all` print bare slugs for loops like the ones above.

`.github/workflows/refresh-dag.yml` runs the same two loops three times each
weekday (07:00 / 12:00 / 17:00 Mountain) and commits any change.

## Conventions that are easy to get wrong

- The dependency column is **`Blocking Issues`**. Renamed from `Blocking Epics`
  on 2026-08-28, because a story can gate an epic too. Readers accept the old
  header via `COLUMN_ALIASES`, so exports predating the rename still load.
- **Run `python3 tools/validate_tracker.py` before trusting a DAG.** A blocker
  that resolves to nothing draws a phantom node under *other tracker* that is
  indistinguishable from a real cross-team dependency - that is exactly what
  `Unknown` did on 2026-08-27. The validator resolves blockers across *every*
  tracker, so a legitimate cross-team reference is silent.
- The tracker's grouping column is **`Capability`**. It accepts **two spellings**
  and canonicalises to the capreq slug at load, exactly as `COLUMN_ALIASES` does
  for a renamed header:
    - a **capreq slug** (the capreq filename with `capreq-` dropped), which
      resolves to `capreq-<slug>.md` in `prak-v-model`; and
    - a **Jama document key** (`PLAT3-PRD_Rqmts-4269`), which the trackers moved
      to on 2026-09-05 because Smartsheet can hyperlink a key straight into Jama.
  The key is an alias, not an identity: `capability-jama.json` maps it back, and
  the slug is still what resolves to the CAP-nn id, title and priority. Without
  that mapping every tile degrades to a raw key and every row fails validation -
  which is exactly what happened when the column was repointed. Renamed from
  `Initiative` on 2026-08-18.
- Electronics epics are project **`ET`**, not `MCHTRNCS`. A Jira search scoped to
  `MCHTRNCS` will not find them - this already caused one wrong conclusion.
- `Blocking Issues` direction is **blocker -> dependent**. `(hard)` means cannot
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
  the capability layer, or it falls back to `data/shared/capability-meta.json`,
  or to bare slugs. Override with `--vmodel`. A fallback run now says so on
  stderr - if you see that note, the capability labels may be stale.
- Priorities are MoSCoW (`Must Have`/`Should Have`/`Could Have`/`Will Not Have`),
  pre-filled from the epic. Do not edit them in meetings.
- A tracker may carry **child rows** - one per story, indented under its epic.
  They are skipped structurally: `load_live` drops any row with a `parentId`,
  and `load_csv` (which has no hierarchy to read) drops any `Epic` id that is
  not a slug. Relying on the child's `Epic` cell being blank was a convention,
  not a rule - the Embedded tracker has 187 story rows, and one stray id would
  have drawn a story as an epic.
- **`Eval Status`** is optional and read for display only - never for an edge, a
  count, or a grouping. `Estimated` draws a green outline on the graph node and a
  green stripe plus chip on the inventory card. A tracker or hand export without
  the column still renders, just without the marker, which is why it lives in
  `OPTIONAL_COLS` rather than `COLS`.
- The graph encodes three things at once, on three separate channels: **fill** is
  MoSCoW priority, **border width** is 2TS required, **border colour** is
  `Eval Status = Estimated`. Adding a fourth needs a new channel, not a reuse.
- **`Story Points` is never typed.** It is a *conditional column* formula:
  `=IF(JiraType@row = "Epic", SUM(CHILDREN()), ROUNDUP(Duration@row / 2))`. The
  meeting's input is **`Duration` in days on story rows**; points are derived and
  rolled up, and the column is locked. Renamed from `Time per Story (points)` on
  2026-09-01. No generator reads it. Keeping the epic/story split *inside* the IF
  is what makes a column formula workable - a bare `=SUM(CHILDREN())` column
  formula would apply to every row.
- **Points are not days** (1->2, 2->3, 3->5, 5->10, no 4). `ROUNDUP(Duration/2)`
  inverts that table exactly at 2d/3d/5d/10d, so it is a derivation and not an
  approximation - but only while Durations stay on that set. 7d yields 4, and
  there is no 4 on the scale. `Epic Total (days)` was dropped from the contract
  on 2026-09-01~~; it still exists on the sheet, repurposed to mirror an epic's Duration, and is deliberately unchecked because nothing reads it~~.
- **Two independent notions of "is this an epic" now exist and must agree.** The
  generators use row hierarchy (`parentId` live, slug pattern on CSV); the sheet's
  column formulas use the `JiraType` cell. A row where they disagree computes its
  numbers on one branch while the graph draws it on the other, silently.
  `validate_tracker.py --live` cross-checks them.
- **A duplicate `Epic` id is an error, not a merge.** Every lookup is a dict keyed
  by that id, so a second row with the same slug takes the graph node while both
  sit in the inventory and the header counts one epic too many. The generator now
  keeps the first, names the drop on stderr, and the validator reports it.

## The capability layer

Everything this repo knows about a capability - the PRD id `CAP-nn`, the human
title and the MoSCoW priority - is read from the `capreq-*.md` **frontmatter** in
[`asirobots/prak-v-model`](https://github.com/asirobots/prak-v-model). That repo
is the source of record; **none of it is maintained by hand here.**

```
prak-v-model/product/requirements/product/capreq-motion-authorization.md
---
id: capreq-motion-authorization
prd-id: CAP-01              -> cap_id
title: Motion Authorization -> title
priority: Must Have         -> priority
jama-id: 12345              -> jama_id   (NOT UPSTREAM YET - see below)
---
```

**The capability's issue link is Jama, not Jira, as of 2026-09-05.** Jira
Initiatives, Objectives and Epics are being retired: ASI DevOps syncs Jama
`User Story` to Jira `Story` for sprint tracking, and the relationship from a
story up to the PRAK System Requirement it supports lives in Jama. There is no
longer a Jira issue at the capability layer to point at, so the tiles and the
landing-page capability table link to Jama.

The map is `data/shared/capability-jama.json` - a hand-maintained **input**,
listing all 15 capabilities. (Jama is the requirements system of record, so every
capreq exists there; the old 9-of-15 split was a Jira artefact and does not carry
over.) A value is either a bare item id, substituted into the file's
`url_template`, or a complete URL used verbatim. Every build names the slugs
still missing one:

```
note: 15 capability tile(s) have no Jama link yet: blackbox-data-off-load-to-cloud, ...
      Fill them in data/shared/capability-jama.json.
```

`jama-id` in capreq frontmatter **wins** over that file, exactly as `jira-key`
used to. The reader already supports it, so adding it upstream needs no change
here - and when every capreq carries it, delete `capability-jama.json`.

`data/shared/capability-meta.json` is a **write-through cache** of that read, not
an input: when the checkout is present the generator rewrites it. It is committed
so a checkout without the sibling repo still renders labelled tiles, and so the
public site does not depend on an internal repo at render time. A run that falls
back to the cache prints a note on stderr.

`prak-v-model` is **INTERNAL** and this repo is public, so the scheduled refresh
checks it out with a `VMODEL_READ_TOKEN` secret. That step is
`continue-on-error` - without it the refresh still runs, just from the cached
capability labels - and the step after it posts a job-summary warning when the
checkout did not land, so a silently rotated credential surfaces instead of
quietly going stale. See TODO.md for what that token currently is and why.

## Current state

The Embedded tracker of record consolidated on 2026-08-31 onto
`Embedded-Core Epic Decomp` (sheet `7348278000570244`, workspace
`prak-sysreq-decomposition`), so the team maintains one sheet rather than two.
**We own it** - `c00236@contractor.asirobots.com` is Owner, David Hayes is Admin,
and he granted us Admin on 2026-08-31. Column structure is writable, not just
cell values, so nothing on this sheet is blocked on someone else's permission.

Embedded-Core and Electronics are live: 102 epics, 62 evaluated, with the first blockers
recorded (Embedded 2 hard edges; Electronics 1 hard + 8 soft, 9 of them still
`[guess]`). Only 11 rows carry a `Blocking Issues` value because the evaluation
meetings have not all happened yet. `dependency-dag.example.*` shows what a fully
populated DAG looks like.

ODOA, GNC and Mobius are registered containers only - no snapshot, no DAG, no
progress numbers, and a "not yet onboarded" card on the landing page. The
Embedded tracker already names one cross-team blocker, `ODOA-5527`, which renders
as an external node until ODOA has a tracker of its own to resolve it against.

See [TODO.md](TODO.md) for open work.
