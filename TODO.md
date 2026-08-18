# TODO

Owner: Patrick McKee, serving as SE for both VSP-Embedded and Electronics.

## Electronics Epic Dependency DAG

Status: **DAG built and generating** from `prak-v-model`. Two things are still
open: Jira keys, and a Smartsheet tracker to replace the v-model as the source.

### Decision: isolated tracking

Electronics tracking is **separate** from Embedded-Core: separate tracker,
separate diagrams, separate standing agenda. The two epic sets are disjoint - of
the 15 Electronics epics, **zero** appear in the 87-row Embedded-Core tracker -
so splitting them loses nothing.

The teams overlap only **above** the epic layer, at the shared Jira parent issues
(PRD Capability Requirements, `CAP-nn` / `product/requirements/product/capreq-*.md`
in `prak-v-model`). Cross-team relationships therefore get expressed at the
capability level, not in a tracker's `Blocking Epics` column. Do not try to encode
cross-team edges in either sheet: `Blocking Epics` resolves epic ids within one
sheet only, and a dangling reference silently drops the edge.

Both teams' epics do map onto the same capabilities, so the capability grouping is
directly comparable across the two DAGs:

| Capability | Embedded epics | Electronics epics |
|------------|---------------:|------------------:|
| CAP-01 Motion Authorization | 10 | 5 |
| CAP-03 Path Execution and Objectives Translation | 12 | 2 |
| CAP-08 Tele-operation | 11 | 7 |
| CAP-09 Observable Runtime State | 1 | 1 |
| CAP-02, CAP-04, CAP-05, CAP-06, CAP-07 | 53 | 0 |

### Done 2026-08-18

- [x] Source epic set identified: 15 epics with `platform-team: Electronics` in
      `prak-v-model/agile-planning/epics/`, all also `Allocation: Electronics`.
- [x] Capability resolved for all 15 by following each epic's `parent-initiative`
      to that initiative's `parent-capability-requirement`. 4 capabilities, no
      unmapped epics.
- [x] Snapshot written: `data/tracker-snapshot-electronics.csv`, same 7-column
      shape the generator reads.
- [x] Generator parameterized with `--sheet-url` and `--title`, so a second
      team's DAG no longer inherits the Embedded-Core heading or tracker link.
      `--sheet-url ""` omits the link when there is no tracker to open.
- [x] DAG generated to `agile-planning/dependency-dag-electronics/`.
- [x] Separate standing agenda forked:
      `agile-planning/meeting-agenda/standingagenda-electronics.{txt,html}`.
      The Embedded pair was renamed to `standingagenda-embedded.*` so neither
      file is the unlabeled default.

### Correction logged 2026-08-18

An earlier pass recorded that the 15 Electronics epics did not exist in Jira.
That was wrong: they are project `ET` (Electrical Team), keys `ET-2951` through
`ET-2965`, team `Electrical Platform`. The search that produced the wrong answer
was scoped to `project = MCHTRNCS`, which holds the Embedded epics and could
never have matched. Keys are now filled in and the DAG links to them.

The same export also supplied the shared capability parents as Jira `Initiative`
issues (`MCHTRNCS-259`..`-266`, `-268`), and above them 6 `Objective` issues
(the Use Cases, `MCHTRNCS-109`/`110`/`111`/`112`/`243`/`267`).

### Still open

| Need | Why | Who |
|------|-----|-----|
| Electronics tracker sheet | The DAG reads `prak-v-model` today, so it reflects the repo rather than meeting decisions. `2TS Required`, `Story Count`, estimates, and `Blocking Epics` have nowhere to live until a sheet exists, which means the Electronics DAG cannot gain edges. | Patrick |
| RACI for the Electronics meeting | The forked agenda carries `TBD` for the SME, capacity, and 2TS-consulted roles. Embedded roles do not carry over automatically. | Patrick + Clint Jones |

### Creating the tracker

Mirror the Embedded-Core sheet exactly: the 7 generator columns (`Epic`,
`Jira Key`, `Title`, `Capability`, `Baseline Priority`, `2TS Required`,
`Blocking Epics`) plus the meeting-input columns (`Batch`, `2TS Rank`,
`Story Count`, `Story Titles`, `Time per Story (days)`, `Epic Total (days)`,
`Owner`, `Confidence`, `Eval Status`). `Capability` holds a capreq slug - the
capreq filename with the leading `capreq-` dropped - which is how the generator
resolves the `CAP-nn` id and title. Seed the rows from
`data/tracker-snapshot-electronics.csv`.

Then switch the generator over; nothing else changes:

```bash
python3 tools/build_dependency_dag.py --live \
  --sheet-id <ELECTRONICS_SHEET_ID> \
  --sheet-url <ELECTRONICS_SHEET_URL> \
  --outdir agile-planning/dependency-dag-electronics \
  --basename dependency-dag \
  --title "Electronics Epic Dependency DAG"
```

## Embedded-Core

- [ ] Populate `Blocking Epics` in the tracker during the evaluation meetings.
      Until then the real DAG renders 0 edges across all 87 epics.
- [ ] Commit the scheduled refresh workflow. It is written and sitting
      **untracked** at `.github/workflows/refresh-dag.yml`, but GitHub rejected
      the push: the current OAuth token has scopes `gist`, `read:org`, `repo` and
      lacks `workflow`, so it may not create files under `.github/workflows/`.
      Fix with `gh auth refresh -s workflow` (interactive), then
      `git add .github/workflows/refresh-dag.yml && git commit && git push`.
      It also needs the `SMARTSHEET_ACCESS_TOKEN` repo secret to actually run.
- [x] ~~Reconcile 40 unmapped tracker rows.~~ Done 2026-08-18: the tracker's
      `Initiative` column was renamed to `Capability` and all 87 rows populated
      with capreq slugs. All 87 now map to one of 9 capabilities (CAP-01 through
      CAP-09), and the unassigned group is gone.
- [ ] 40 of the 87 tracker rows still have no matching epic file in
      `prak-v-model/agile-planning/epics/` (47 rows do; 68 epic files exist, 21
      of them for other teams). The capability grouping no longer depends on
      those files, so this is a v-model completeness question, not a DAG blocker.
- [x] ~~Reconcile the tracker against Jira.~~ Done 2026-08-18: Jira holds 93
      PRAK-labelled epics against the tracker's 87. The 6 extras are
      MCHTRNCS-132, -136, -198, -201, -204 and one more, all `Platform Team`
      GNC or Perception. The tracker is correctly scoped to VSP-Embedded; 87 is
      right, not short by 6.
- [x] ~~Decide whether the committed snapshot should be a full-fidelity
      export.~~ Decided 2026-08-18: keep it to the 7 generator columns. The other
      9 are meeting scratch space (`Batch`, `2TS Rank`, `Story Titles`, `Owner`,
      ...) and this repo is public. `tools/export_snapshot.py` writes exactly
      those 7 from the live sheet.

## Repo hygiene

- [x] ~~Commit and push.~~ Done 2026-08-18.
- [x] ~~Add a `CLAUDE.md`.~~ Done 2026-08-18: records the two-team/one-capability
      model, the hard rules (nothing hand-drawn, never commit raw exports to this
      public repo), the layout, the full rebuild sequence, and the conventions
      that are easy to get wrong.
- [ ] Turn on GitHub Pages: Settings > Pages > source `main`, root. Then add the
      `SMARTSHEET_ACCESS_TOKEN` secret so the refresh workflow can run.
- [ ] `data/prak_jira_snapshot-20260818.csv` is gitignored, not pruned. If the
      Jira export should be committed in some form, prune it to the used columns
      first: of its 508 columns only 58 carry data, and three of those are ECR
      field templates embedding internal labor rates.
