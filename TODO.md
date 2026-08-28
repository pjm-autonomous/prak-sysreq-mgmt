# TODO

prak-sysreq-mgmt **In-Progress: tooling complete, decomposition not started**

Owner: Patrick McKee, serving as SE for VSP-Embedded and Electronics.
Last updated 2026-08-26.

## Where this stands

The generator, the DAGs, the published site, and the agendas are done. What is
outstanding is **data**, not code: 102 epics are loaded and grouped across the two
live teams, 32 of them evaluated, and only 11 rows carry a dependency. Three more
teams — ODOA, GNC, Mobius — are registered containers with nothing in them yet.

| | Embedded-Core | Electronics | ODOA | GNC | Mobius |
|---|---:|---:|---:|---:|---:|
| Epics | 87 | 15 | — | — | — |
| Capabilities | 9 | 4 | — | — | — |
| Evaluated (`2TS Required` set) | 17 | 15 | — | — | — |
| Rows with dependencies recorded | 2 | 9, all provisional | — | — | — |
| Tracker | live | live | none | none | none |
| Jira project | `MCHTRNCS` | `ET` | `ODOA` | `GNC` | `MP` |

Published: https://pjm-autonomous.github.io/prak-sysreq-mgmt/ (rebuilds on push).

### Next session

1. Run the first Electronics evaluation meeting, or confirm the 9 provisional
   `[guess]` dependencies, whichever comes first.
2. After any meeting: export the sheet to CSV, then
   `python3 tools/build_dependency_dag.py --team <t> --csv <export>` and
   `python3 tools/build_index.py`, commit, push. The site updates itself.
3. If IT ticket #help00004986 has landed, mint the Smartsheet personal API
   token, set `SMARTSHEET_ACCESS_TOKEN` locally for `--live`, and add it as a
   repo secret so `.github/workflows/refresh-dag.yml` (already committed, cron
   three times each weekday, 07:00 / 12:00 / 17:00 Mountain) stops failing on
   its token check.

## Fixed 2026-08-26: the offline refresh never wrote a snapshot

Found by test-running a fresh Embedded export through the documented loop.
PUBLISHING.md said `build_dependency_dag.py --csv <export>` rebuilt "that team's
snapshot + DAG" — it never wrote a snapshot at all, so following the documented
procedure regenerated the DAG while leaving `data/<team>/tracker-snapshot.csv`
untouched, and `build_index.py` kept reporting the previous progress numbers off
the stale file. That is the exact failure the generator's own comments warn about,
and it applied to the *only* refresh route available until the Smartsheet token
lands.

- [x] ~~Add `--from-csv` to `tools/export_snapshot.py`~~ so a hand export goes
      through the same prune-and-sort as `--live`. Verified: re-running the loop
      over the 2026-08-26 export reproduces the committed snapshot byte-for-byte
      and leaves the DAG identical apart from its timestamp.
- [x] ~~Correct the PUBLISHING.md refresh loop~~ to the real 5 steps.

Related: output is input-order dependent. The live route sorts by epic id, a raw
export is in tracker row order, so pointing the generator straight at an export
reorders the whole epic-data block in the viewer. Routing both through
`export_snapshot.py` is what keeps the committed HTML from churning.

## Capability layer: finish the move to prak-v-model frontmatter

The capability id, title, priority and Jira Initiative key now all come from
`capreq-*.md` frontmatter in `asirobots/prak-v-model`. Three things close it out:

- [ ] **Land the upstream `jira-key` change.** Adds `jira-key:` to the 9 capreqs
      that have a Jira Initiative, plus the field in
      `templates/capability-requirement.md`. Local branch `feat/capreq-jira-key`,
      **unpushed, queued behind PR #34** (*Feature/mission objectives use cases*).
      Rebased onto `main` @ `063b2f2` (post-#32) so it is ready to push when #34
      clears. Verified: `validate-artifacts` clean over 340 files, `dist/`
      unchanged, all 9 keys confirmed against Jira as `Initiative` issues whose
      Summary title matches the capreq title.

      **This repo does not wait on it.** `main` has no `jira-key` today, the
      committed cache correctly reflects that, and `capability-jira.json` supplies
      all 9 keys with a per-run stderr note naming them. Output is identical
      either way — the only difference is which file the key came from.
- [x] ~~**Set the `VMODEL_READ_TOKEN` repo secret**~~ Done 2026-08-27. The
      scheduled refresh now checks out `asirobots/prak-v-model` and regenerates
      the capability cache from source. Verified by A/B dispatch: run
      `33106528297` (secret unset) logged
      `note: .../.vmodel not checked out ... may be stale` and raised the
      "capability source unavailable" notice; run `33107998379` (secret set)
      logged `capability source checked out at .vmodel`, raised no such notice,
      and committed nothing — correct, because the cache already matched
      `prak-v-model` `main`.

      > **⚠ EXPIRES Wed 16 Sep 2026.** `friday github_review — brief` is a
      > 30-day token issued 17 Aug 2026. On expiry the checkout starts failing,
      > `continue-on-error` masks it, and **the job stays green** — the only
      > signal is the notice and job summary from the "Did the capability source
      > land?" step. Treat that date as a decision point, not a renewal chore:
      > regenerating this token invalidates it wherever Friday uses it (its value
      > is held server-side by the claude.ai connector and cannot be read back),
      > so the better move is minting the dedicated `prak-v-model` +
      > Contents:Read PAT below.

      **Decision 2026-08-26: reuse the existing `friday github_review` PAT.**
      Accepted with eyes open, after the two tighter options were ruled out:

      | Option | Outcome |
      |--------|---------|
      | Read-only deploy key | **Blocked.** asirobots disables deploy keys by org/enterprise policy — HTTP 422 "Deploy keys are disabled for this repository". Enabling them is a global policy change, not a repo-admin toggle. Do not retry this. |
      | New narrow PAT (`asirobots` owner, prak-v-model only, Contents:Read) | Viable, needs an ASI approval round. Deferred, not rejected. |
      | Reuse `friday github_review` | **Chosen.** Works today, no approval. Read access to `prak-v-model` confirmed 2026-08-26 — both the Contents permission and the repository scope. |

      Two known, accepted consequences:

      1. **Blast radius.** That PAT carries read on actions, discussions, issues,
         merge queues, pages and pull requests across asirobots — far more than
         the `Contents:Read` this job uses — and it now sits in a *public* repo's
         secret store. Anyone who gains write on this repo can read all of it.
         Fork PRs cannot reach it (no `pull_request` trigger), so the exposure is
         write-access-to-this-repo, which today is one person.
      2. **Lifecycle coupling.** Rotating or revoking it for the review tooling
         breaks this job. Because the checkout is `continue-on-error`, that would
         degrade the refresh to cached capability labels *silently* — so the
         "Did the capability source land?" step was added to post a `::notice::`
         and a job-summary warning when the checkout does not produce
         `.vmodel/product/requirements/product`.

- [ ] **Narrow `VMODEL_READ_TOKEN` to a dedicated Contents:Read PAT.** Follow-up
      to the decision above. **Do this by 16 Sep 2026**, when the shared token
      expires — that is the natural moment, since the alternative is regenerating
      a token other tooling depends on. Nothing
      in the workflow changes — same secret name, same `token:` input — so this is
      a pure credential swap. Resource owner must be `asirobots`, not the personal
      account; getting that wrong yields a 404 that reads like a typo'd repo name.
      Verify with a *Contents* call, not a repo call:
      `gh api repos/asirobots/prak-v-model/contents/product/requirements/product`
      should return 15 entries — `gh api repos/asirobots/prak-v-model` succeeds on
      Metadata alone and proves nothing.

      Placement, if ever redone: the secret belongs on
      **`pjm-autonomous/prak-sysreq-mgmt`** (the repo whose workflow *runs*), under
      *Settings > Secrets and variables > **Actions***, never on prak-v-model and
      never under the Agents tab — Agents secrets are for Copilot coding-agent
      sessions and are invisible to `${{ secrets.* }}` in a workflow run.

- [ ] **Delete `data/shared/capability-jira.json`** and `merge_capability_jira()`
      once the PR is merged and every capreq in `main` carries `jira-key`. The
      generator prints a note naming any slug still relying on the legacy file,
      so an empty note means it is safe to remove.

The 6 capabilities with no Jira Initiative (`developer-tooling-update-path`,
`perception-for-manipulation`, `robot-localization`, `robot-web-application`,
`software-update-and-rollback`, `video-recording-and-streaming`) are
deliberately left without the field rather than given a placeholder.

## ODOA / GNC / Mobius - registered, not onboarded

Containers exist and the registry knows them; nothing else does.

| | ODOA | GNC | Mobius |
|---|---|---|---|
| Jira project | `ODOA` (ODOA Platform) | `GNC` (GNC Platform) | `MP` (Mobius Platform) |
| PRAK epics in Jira | none yet | none yet | none yet |
| Smartsheet tracker | none | none | none |
| Container | `data/odoa/`, `agile-planning/odoa/` | `data/gnc/`, `agile-planning/gnc/` | `data/mobius/`, `agile-planning/mobius/` |

- [ ] Decompose each scope through [WORKFLOW.md](WORKFLOW.md) steps 1-11 and
      import the epics to Jama and Jira.
- [ ] Stand up each team's Smartsheet tracker from the shared template
      (steps 12-14), then set `sheet_id`, `sheet_url`, and `refresh: True` in
      that team's entry in `tools/teams.py`. Nothing else needs editing - the
      snapshot path, output directory, and agenda path all derive from the slug.
- [ ] Write each team's `agile-planning/<slug>/standingagenda.*` once the epic
      count and cadence are known.
- [ ] **`ODOA-5527` is already named as a blocker** in the Embedded-Core
      tracker. It renders as an external node under *other tracker* today; once
      ODOA has a snapshot it resolves to a real epic with a title and Jira link.
      Confirm the id is right before the ODOA decomposition starts.

## Electronics Epic Dependency DAG

Status: **live.** Tracker exists (sheet `2558444740497284`), 15 epics, 9
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
- [x] ~~Commit the scheduled refresh workflow.~~ Done:
      `.github/workflows/refresh-dag.yml` is tracked and runs three times each
      weekday (07:00 / 12:00 / 17:00 Mountain), looping over
      `python3 tools/teams.py --refreshable`.
- [ ] Add the `SMARTSHEET_ACCESS_TOKEN` repo secret. This is a Smartsheet
      **personal API token**, not the Claude Connector — the runner is headless
      and calls the REST API directly, so the connector cannot stand in for it.
      Blocked on IT ticket #help00004986, and the account that would mint it is
      not provisioned yet, so treat this as open-ended.
      Until it lands the scheduled run **skips the tracker pull and carries on**
      rather than failing: it emits a `::notice::`, writes a "Tracker pull
      skipped" job summary, rebuilds from the committed snapshots, and titles any
      resulting commit *Rebuild dependency DAGs from capability metadata* so
      `git log` never claims a tracker read that did not happen. Changed
      2026-08-26 — a red X every weekday is how a scheduled job teaches everyone
      to ignore it.
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
      export.~~ Decided 2026-08-18: keep it to the generator columns. The other
      9 are meeting scratch space (`Batch`, `2TS Rank`, `Story Titles`, `Owner`,
      ...) and this repo is public. `tools/export_snapshot.py` writes exactly
      those 7 from the live sheet.

## Blocked on access

- [ ] **Smartsheet API token.** Patrick's permission level excludes API keys.
      IT ticket **#help00004986**, submitted 2026-08-18. Until it lands, `--live` and
      `tools/export_snapshot.py` cannot run, and the scheduled refresh workflow
      cannot work even once it is committed.
      **Working path meanwhile:** in Smartsheet, File > Export > Export to CSV,
      then rebuild from the export:
      ```bash
      python3 tools/build_dependency_dag.py --team electronics --csv path/to/export.csv
      python3 tools/build_index.py
      ```
      Committing the refreshed `data/<team>/tracker-snapshot.csv` keeps the
      published site current, since Pages rebuilds on every push.
      Ask IT for: a Smartsheet API access token (Personal Settings > API Access)
      with read on sheets `5240263122308996` and `2558444740497284`.
- [x] ~~**GitHub Actions workflow creation.**~~ Resolved: the `workflow` OAuth
      scope was granted and `.github/workflows/refresh-dag.yml` is committed and
      tracked. It still needs `SMARTSHEET_ACCESS_TOKEN` as a repo secret to do
      anything - see the entry above.

## Publishing

**GitHub Pages is live: https://pjm-autonomous.github.io/prak-sysreq-mgmt/**

It does not depend on a workflow. The site is `build_type: legacy`, serving
`main` at root, which means GitHub rebuilds it itself on every push - it has
already rebuilt on `dce5b23` and `5226b20` with no Actions involvement. The
scheduled refresh workflow is a convenience on top of that, not a dependency.

So DAGs are published as pages today, not only as artifacts. What is manual until
the Smartsheet token arrives is the *refresh*: export CSV, regenerate, commit,
push - and the site updates itself from there.

## Session log

### 2026-08-18

- Built the generator, both DAGs, the two-level capability drill-down viewer,
  the published landing page, the agendas, and `tools/teams.py`.
- Tracker grouping column renamed `Initiative` -> `Capability`; all 87 Embedded
  rows populated with capreq slugs, closing the 40-row unmapped gap.
- Electronics tracker created and wired in; 15 epics, Jira keys `ET-2951`..`-2965`.
- Two generator defects found and fixed, both silent: `Blocking Epics` entries
  were split on commas inside qualifiers (would have shown 0 edges for all 9
  Electronics dependencies), and unresolvable refs were dropped rather than
  drawn (made cross-team dependencies invisible).
- One wrong finding recorded and corrected: "Electronics epics do not exist in
  Jira" came from a JQL scoped to `project = MCHTRNCS`; they are in `ET`.
- GitHub Pages enabled and verified live.

## Repo hygiene

- [x] ~~Commit and push.~~ Done 2026-08-18.
- [x] ~~Add a `CLAUDE.md`.~~ Done 2026-08-18, updated 2026-08-26 for the
      five-team container layout: records the shared-capability model, the hard
      rules (nothing hand-drawn, never commit raw exports to this public repo),
      the layout, the full rebuild sequence, and the conventions that are easy to
      get wrong.
- [x] ~~Turn on GitHub Pages.~~ Done - the site is live at
      https://pjm-autonomous.github.io/prak-sysreq-mgmt/.
- [ ] `data/prak_jira_snapshot-20260818.csv` is gitignored, not pruned. If the
      Jira export should be committed in some form, prune it to the used columns
      first: of its 508 columns only 58 carry data, and three of those are ECR
      field templates embedding internal labor rates.
