# TODO

Owner: Patrick McKee, serving as SE for both VSP-Embedded and Electronics.

## Electronics Epic Dependency DAG

Status: **blocked on Jira keys and a tracker sheet.** Source epic set is already
identified (see below).

### Decision: isolated tracking

Electronics tracking is **separate** from Embedded-Core. Separate Smartsheet
tracker, separate diagrams, separate standing agenda. The two epic sets are
disjoint, so nothing is lost by splitting them: of the 15 Electronics epics in
`prak-v-model`, **zero** appear in the 87-row Embedded-Core tracker.

The teams overlap only **above** the epic layer, at the shared Jira parent issues
(PRD Capability Requirements, `CAP-nn` / `product/requirements/product/capreq-*.md`
in `prak-v-model`). Cross-team relationships therefore get expressed at the
capability level, not in a tracker's `Blocking Epics` column.
Do not try to encode cross-team edges in either sheet: `Blocking Epics` resolves
epic ids within one sheet only, and a dangling reference silently drops the edge.

### Source epic set (15, from `prak-v-model`)

`platform-team: Electronics` in `prak-v-model/agile-planning/epics/`. All 15 also
carry `Allocation: Electronics`.

```
epic-accept-c2-movement-request           epic-publish-teleop-override-notification
epic-acknowledge-path-to-c2               epic-publish-teleop-situational-feedback
epic-confirm-auto-manual-in-auto          epic-publish-visible-operating-indications
epic-detect-teleop-link-loss-and-report   epic-record-recovery-acknowledgment
epic-no-video-stream-on-teleop-icd        epic-report-execution-events-to-c2
epic-publish-motion-authorization-state   epic-require-los-ack-at-session-init
epic-publish-path-execution-telemetry     epic-validate-teleop-icd-at-session-init
                                          epic-validate-teleop-input-against-icd
```

Regenerate that list rather than trusting this copy:

```bash
grep -rl "^platform-team: Electronics" ../prak-v-model/agile-planning/epics/*.md \
  | xargs -n1 basename | sed 's/\.md$//' | sort
```

### Blocked on

| Need | Why | Who |
|------|-----|-----|
| Jira keys for the 15 Electronics epics | The epic markdown files in `prak-v-model` carry no `jira-key` frontmatter, and none of the 15 appear in the Embedded-Core `MCHTRNCS-###` range currently tracked. Either the Jira epics do not exist yet or the mapping is unrecorded. The tracker's `Jira Key` column and the generated node links both need them. | Patrick (as Electronics SE) |
| Electronics tracker sheet (Smartsheet URL + numeric id) | No such sheet exists. An API search for `Epic Decomposition Tracker` returns only Embedded-Core (id `8066207570677636`). | Patrick |

### Steps once unblocked

1. Create the Electronics tracker with the **same 7 columns the generator reads**:
   `Epic`, `Jira Key`, `Title`, `Capability`, `Baseline Priority`, `2TS Required`,
   `Blocking Epics`. `Capability` holds a capreq slug - the capreq filename with
   the leading `capreq-` dropped - which is how the generator resolves the
   `CAP-nn` id and title. Mirror the Embedded-Core sheet's meeting-input columns
   (`Batch`, `2TS Rank`, `Story Count`, `Story Titles`, `Time per Story (days)`,
   `Epic Total (days)`, `Owner`, `Confidence`, `Eval Status`) so the two agendas
   stay procedurally identical even though the meetings are separate.
2. Populate from the 15 epics above. `Capability` comes from following each
   epic's `parent-initiative` to that initiative's
   `parent-capability-requirement`; `Baseline Priority` from the epic's
   `priority` field.
3. Add `--sheet-url` to the generator **before** the first Electronics run.
   `SHEET_URL` is currently a module constant at
   [tools/build_dependency_dag.py:60](tools/build_dependency_dag.py#L60), consumed at
   line 734 to build the "open tracker" link in the HTML. `--sheet-id` changes which
   sheet is read but not which sheet is linked, so an Electronics DAG would link back
   to the Embedded-Core tracker. `load_live` already receives the sheet's `permalink`
   from the API response and discards it, so deriving it is a few lines.
4. Generate into a separate directory:

   ```bash
   python3 tools/build_dependency_dag.py --live \
     --sheet-id <ELECTRONICS_SHEET_ID> \
     --sheet-url <ELECTRONICS_SHEET_URL> \
     --outdir agile-planning/dependency-dag-electronics \
     --basename dependency-dag
   ```

5. Add a separate Electronics standing agenda:
   `agile-planning/meeting-agenda/standingagenda-electronics.txt` and its HTML twin,
   forked from the Embedded-Core pair and pointed at the Electronics tracker.
   Rename the existing pair to `standingagenda-embedded.*` at the same time, so
   neither file is the unlabeled default.
6. Add an `## Electronics Epic Dependency DAG` section to [README.md](README.md)
   mirroring the Embedded-Core section.

## Embedded-Core

- [ ] Populate `Blocking Epics` in the tracker during the evaluation meetings.
      Until then the real DAG renders 0 edges across all 87 epics.
- [ ] Re-run the generator after each meeting day, or put `--live` on a schedule.
- [x] ~~Reconcile 40 unmapped tracker rows.~~ Done 2026-08-18: the tracker's
      `Initiative` column was renamed to `Capability` and all 87 rows populated
      with capreq slugs. All 87 now map to one of 9 capabilities (CAP-01 through
      CAP-09), and the unassigned group is gone.
- [ ] 40 of the 87 tracker rows still have no matching epic file in
      `prak-v-model/agile-planning/epics/` (47 rows do; 68 epic files exist, 21
      of them for other teams). The capability grouping no longer depends on
      those files, so this is a v-model completeness question, not a DAG blocker.
- [ ] `data/tracker-snapshot.csv` carries only the 7 generator columns, not the
      full 16-column sheet. Decide whether the committed snapshot should be a
      full-fidelity export.

## Repo hygiene

- [ ] Commit and push. `agile-planning/`, `data/`, `tools/`, and `TODO.md` are
      untracked; the only commit is the initial one.
- [ ] No `CLAUDE.md` and no `memory/` exist in this repo, so session resume has to
      reconstruct state from file mtimes. Add a `CLAUDE.md` with the current phase
      and checklists, modeled on `prak-v-model/CLAUDE.md`.
