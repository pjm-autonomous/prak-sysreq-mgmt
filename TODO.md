# TODO

Owner: Patrick McKee, serving as SE for both VSP-Embedded and Electronics.

## Electronics Epic Dependency DAG

Status: **live.** Tracker exists (sheet `5660443916849028`), 15 epics, 9
dependencies recorded, DAG generating from it.

### Decision: isolated tracking

Separate tracker, separate diagrams, separate standing agenda. The two epic sets
are disjoint - of the 15 Electronics epics, zero appear in the 87-row
Embedded-Core tracker.

The teams overlap only **above** the epic layer, at the shared PRD Capability
Requirements (Jira `Initiative` issues `MCHTRNCS-259`..`-266`, `-268`). Both
teams' epics map onto the same capabilities, so the capability grouping is
directly comparable across the two DAGs:

| Capability | Embedded | Electronics |
|------------|---------:|------------:|
| CAP-01 Motion Authorization | 10 | 5 |
| CAP-03 Path Execution and Objectives Translation | 12 | 2 |
| CAP-08 Tele-operation | 11 | 7 |
| CAP-09 Observable Runtime State | 1 | 1 |
| CAP-02, CAP-04, CAP-05, CAP-06, CAP-07 | 53 | 0 |

Cross-team dependency is expressed by referencing the other team's epic id in
`Blocking Epics`. It renders as an **external node** rather than resolving, since
`Blocking Epics` only resolves ids within its own sheet. External nodes are drawn
for context and excluded from the referencing team's counts.

### Done 2026-08-18

- [x] Tracker created and populated: 15 epics, capability + priority + Jira keys.
- [x] Jira keys filled: project `ET`, `ET-2951`..`ET-2965`. Each epic's Jira
      parent independently confirms its capability - 15/15 agree with the
      capability resolved through `prak-v-model`.
- [x] Capability tiles link to their shared Jira Initiative parent.
- [x] `tools/teams.py` registry added; both generators read it. `--team embedded`
      / `--team electronics` replace the long per-team command lines.
- [x] **Fixed a silent edge-dropping bug.** `Blocking Epics` entries of the form
      `epic-x (Embedded, soft) [guess]` were split on the comma inside the
      qualifier list, producing garbage refs that then failed to resolve and were
      discarded. All 9 Electronics dependencies would have rendered as zero edges
      while the output looked healthy.
- [x] Cross-team blockers now render as external nodes instead of being dropped,
      labelled with the other team's title and Jira link via `--cross-reference`
      (passed automatically by `--team`).
- [x] Provisional `[guess]` dependencies are parsed, labelled **guess** on the
      edge, and counted separately in the header.

### Still open

| Need | Why | Who |
|------|-----|-----|
| Confirm the 9 provisional dependencies | Every recorded edge is tagged `[guess]` - a working assumption, not a meeting decision. Until confirmed the Electronics critical path is indicative only. | Electronics evaluation meeting |
| Electronics meeting RACI | The agenda carries `TBD` for the SME, capacity, and 2TS-consulted roles. Embedded roles do not carry over automatically. | Patrick + Clint Jones |
| Evaluate the 15 epics | `2TS Required` is `TBD` on all 15; no story counts or estimates yet. | Electronics evaluation meeting |

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

## Blocked on access

- [ ] **Smartsheet API token.** Patrick's permission level excludes API keys; an
      IT help request was submitted 2026-08-18. Until it lands, `--live` and
      `tools/export_snapshot.py` cannot run, and the scheduled refresh workflow
      cannot work even once it is committed.
      **Working path meanwhile:** in Smartsheet, File > Export > Export to CSV,
      then rebuild from the export:
      ```bash
      python3 tools/build_dependency_dag.py --team electronics --csv path/to/export.csv
      python3 tools/build_index.py
      ```
      Committing the refreshed `data/tracker-snapshot*.csv` keeps the published
      site current, since Pages rebuilds on every push.
      Ask IT for: a Smartsheet API access token (Personal Settings > API Access)
      with read on sheets `8066207570677636` and `5660443916849028`.
- [ ] **GitHub Actions workflow creation.** The current OAuth token has scopes
      `gist`, `read:org`, `repo` and lacks `workflow`, so
      `.github/workflows/refresh-dag.yml` cannot be pushed. It is written and
      sitting untracked. Fix with `gh auth refresh -s workflow`, then commit that
      one file. Blocked behind the Smartsheet token regardless - the workflow
      needs `SMARTSHEET_ACCESS_TOKEN` as a repo secret to do anything.

## Publishing

**GitHub Pages is live: https://pjm-autonomous.github.io/prak-sysreq-mgmt/**

It does not depend on a workflow. The site is `build_type: legacy`, serving
`main` at root, which means GitHub rebuilds it itself on every push - it has
already rebuilt on `dce5b23` and `5226b20` with no Actions involvement. The
`workflow` scope block does **not** affect publishing; it only blocks automating
the tracker refresh.

So DAGs are published as pages today, not only as artifacts. What is manual until
the Smartsheet token arrives is the *refresh*: export CSV, regenerate, commit,
push - and the site updates itself from there.

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
