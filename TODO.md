# TODO

Task list for `prak-sysreq-mgmt` (`pjm-autonomous/prak-sysreq-mgmt`). Paths are
relative to the repo root. The sibling `prak-v-model` keeps its own `TODO.md`;
items that cross the two name the other side explicitly.

Status: **In-Progress** — tooling complete, decomposition ~60% evaluated.
Owner: Patrick McKee
Role: SE for VSP-Embedded and Electronics
Updated: 2026-09-02

## Where this stands

The generator, the DAGs, the published site, and the agendas are done. What is outstanding is **data**, not code: 102 epics are loaded and grouped across the two live teams, 62 of them evaluated, and only 11 rows carry a dependency.
Three more teams — ODOA, GNC, Mobius — are registered containers with nothing in them yet.

Embedded's tracker of record is `Embedded-Core Epic Decomp`, which we own; it carries 187 story rows indented under 46 of its 87 epics, which the generators skip. The old flat sheet is `archived-prak-embedded-core-epics` and is the basis for the template ODOA, GNC and Mobius will onboard from.

| | Embedded-Core | Electronics | ODOA | GNC | Mobius |
|---|---:|---:|---:|---:|---:|
| Epics | 87 | 15 | — | — | — |
| Capabilities | 9 | 4 | — | — | — |
| Evaluated (`2TS Required` set) | 47 | 15 | — | — | — |
| Rows with dependencies recorded | 2 | 9, all provisional | — | — | — |
| Story rows | 187 | — | — | — | — |
| Tracker | live (`Embedded-Core Epic Decomp`, we own it) | live (`prak-electronics-epics`) | none | none | none |
| Jira project | `MCHTRNCS` | `ET` | `ODOA` | `GNC` | `MP` |

Published: https://pjm-autonomous.github.io/prak-sysreq-mgmt/ (rebuilds on push).

### Changed 2026-08-31

- Embedded repointed to `Embedded-Core Epic Decomp` (recorded at the time as David Hayes' sheet - in fact ours, see 2026-09-01); one tracker, not two. Structurally output-neutral — the mermaid graph was byte-identical.
- Story rows excluded from the epic set structurally (`parentId` on the live path, epic-slug pattern on the CSV path) rather than by the convention that a child's `Epic` cell happens to be blank. Verified by injection.
- `Blocking Epics` renamed to `Blocking Issues` in both trackers and the code; `COLUMN_ALIASES` keeps older exports loading.
- Both trackers restored after the 2026-08-27 account reconfiguration: 117 Jira hyperlinks, 8 dropdowns, formulas, no cell errors.
- Added `tools/validate_tracker.py` + `data/shared/tracker-schema.json`, cross-team dependency table, change digest, `/refresh` comment workflow, `CREDENTIALS.md`, and a retry around the Smartsheet API.
- Estimation and confidence rules recorded in the schema: points are not days (1→2, 2→3, 3→5, 5→10), and Confidence has stated criteria.

### Changed 2026-09-01

- **Sheet of record re-verified live.** `7348278000570244` is `Embedded-Core Epic Decomp`; id, URL, name, columns, dropdowns, the 87/187 row split and every cell count match the committed snapshot exactly. Offline pipeline reproduces committed output byte-for-byte apart from its timestamp.
- **Ownership record corrected.** We are **Owner** of that tracker (`c00236@contractor.asirobots.com`) and David Hayes granted us **Admin** on 2026-08-31. Four files said we held Editor and that column structure was someone else's to change. Nothing on that sheet is permission-blocked.
- **`Epic Total (days)` dropped from the contract.** No generator ever read it; its presence on any sheet is now immaterial. David may delete it at will.
- **`Time per Story (points)` renamed `Story Points`**, and re-specified: points on story rows only, `=SUM(CHILDREN())` on the epic row. Repo, schema and the Embedded standing agenda updated; the *Smartsheet* change is still to make.
- **Registry hardened.** `sheet_name` added per team; `load_live` warns when the live sheet name and the registry disagree, and the validator names a sheet the schema has no formula block for. Id addresses, name asserts, URL decorates.
- **Hidden-column question settled by test:** CSV and Excel exports carry hidden columns; only PDF drops them. The `Epic` column being hidden is therefore harmless to the build. Validator reports it as maintenance hygiene, not risk.
- **Two Smartsheet accounts found**, which is what made a working sheet id look wrong - see *Re-authorize the Smartsheet connector* below.

### Next session

1. **Make the two Smartsheet column changes** on `Embedded-Core Epic Decomp`.  
  We hold Admin, so neither needs anyone else:
   - Rename `Time per Story (points)` -> `Story Points`.
   - Put `=SUM(CHILDREN())` in the **Story Points cell of each epic row that has    children** (46 of 87). It must be a *cell* formula, not a column formula - Smartsheet column formulas apply to every row and would overwrite each story's hand-entered estimate. Epics with no children stay blank.
  Do this from the browser, or from Claude *after* the connector is re-authorized. Not before: the current grant is the dead `patrick.mckee-cn47` account, and writing through it stamps that identity
   into the sheet's cell history.
2. **Re-authorize the Smartsheet connector onto `c00236`.** Full procedure in [CREDENTIALS.md](CREDENTIALS.md). The grant is currently on `patrick.mckee-cn47@contractor.asirobots.com`, which reads `Embedded-Core Epic Decomp` (it still holds Admin there) and 403s on `prak-electronics-epics`, `prak-TEMPLATE-epics` and the archived sheet. That asymmetry reads exactly like a wrong sheet id and cost a full verification pass to diagnose. Remove `patrick.mckee-cn47` from the sheet's share list only *after* the new grant is confirmed working.
3. Confirm the 9 provisional `[guess]` Electronics dependencies, or run the first Electronics evaluation meeting, whichever comes first.
4. After any meeting: export the sheet to CSV, then `python3 tools/build_dependency_dag.py --team <t> --csv <export>` and `python3 tools/build_index.py`, commit, push. The site updates itself.
5. If IT ticket #help00004986 has landed, mint the Smartsheet personal API token **under `c00236@contractor.asirobots.com`**, set `SMARTSHEET_ACCESS_TOKEN` locally for `--live`, and add it as a repo secret so `.github/workflows/refresh-dag.yml` (already committed, cron three times each weekday, 07:00 / 12:00 / 17:00 Mountain) stops failing on its token check. Minting it under the old account would reproduce the connector problem in CI.
6. **Verify Michael Anderson can actually edit the tracker.** The Embedded agenda names him Responsible for estimates and story breakdown, but the sheet's item-level share list is only David Hayes, us, and the dead account. He may hold access through the `prak-sysreq-decomposition` workspace - the API's item-scope list would not show that. Confirm before the next meeting.

## Fixed 2026-08-26: the offline refresh never wrote a snapshot

Found by test-running a fresh Embedded export through the documented loop.
PUBLISHING.md said `build_dependency_dag.py --csv <export>` rebuilt "that team's
snapshot + DAG" — it never wrote a snapshot at all, so following the documented
procedure regenerated the DAG while leaving `data/<team>/tracker-snapshot.csv`
untouched, and `build_index.py` kept reporting the previous progress numbers off
the stale file. That is the exact failure the generator's own comments warn about,
and it applied to the *only* refresh route available until the Smartsheet token
lands.

- [x] ~~Add `--from-csv` to `tools/export_snapshot.py`~~ so a hand export goes through the same prune-and-sort as `--live`. Verified: re-running the loop over the 2026-08-26 export reproduces the committed snapshot byte-for-byte and leaves the DAG identical apart from its timestamp.
- [x] ~~Correct the PUBLISHING.md refresh loop~~ to the real 5 steps.

Related: output is input-order dependent. The live route sorts by epic id, a raw
export is in tracker row order, so pointing the generator straight at an export
reorders the whole epic-data block in the viewer. Routing both through
`export_snapshot.py` is what keeps the committed HTML from churning.

## Workflow simplification - explored 2026-08-28

Built: the tracker validator + schema, the comment-triggered refresh, the
cross-team dependency table, the change digest, and CREDENTIALS.md.

Deferred, in rough value order:

- [ ] **`tools/onboard_team.py --slug gnc --sheet-id N`.** Turns WORKFLOW.md steps 12-14 from prose into one command: validate the sheet against `tracker-schema.json`, write the registry entry, pull the first snapshot, build. Worth doing before ODOA/GNC/Mobius onboard, so all three get the same treatment rather than three hand-runs.
- [x] ~~**A simplified Smartsheet tracker template**, for ODOA, GNC and Mobius.~~ Done 2026-08-31: **`prak-TEMPLATE-epics`**, sheet id `4956716494966660`. Structure copied from `archived-prak-embedded-core-epics` with no rows, and the `Epic Total (days)` formula corrected to the agreed points scale (the archived sheet still had the pre-conversion `* 2`). That column was dropped from `tracker-schema.json` on 2026-09-01 and is no longer checked anywhere; it is harmless on the template either way.
 Rehearsed end to end before being declared done: copied it, added two example epics with a dependency between them, and ran the real pipeline - validator 0 errors, snapshot 2 epics, DAG 1 hard edge over 2 capabilities. Rehearsal sheet deleted.
 To onboard a team: copy the template, name it `prak-<slug>-epics`, fill in epics, then `python3 tools/validate_tracker.py --sheet-id <id>` before adding the entry to `tools/teams.py`.
 Original note, kept for the reasoning: **A simplified Smartsheet tracker template**, for ODOA, GNC and Mobius. Lives in the Smartsheet workspace, not the repo - a template is a Smartsheet object, and `tracker-schema.json` already carries the contract the repo needs.
 Source: `archived-prak-embedded-core-epics` (id `5240263122308996`, renamed and moved to an archive folder 2026-08-31 when Embedded switched to `Embedded-Core Epic Decomp`). It is the right basis precisely because it is flat - 87 epic rows, no story children - so a new team starts with the 8 columns the generators read and adds hierarchy only if it wants to.
 Must satisfy `tracker-schema.json`: the 7 required columns plus `Eval Status`, with `Baseline Priority`, `2TS Required`, `Confidence` and `Eval Status` as dropdowns. Verify a new sheet with `python3 tools/validate_tracker.py --sheet-id <id>` before registering it. Confirm whether the API can create a sheet from a template, which would let `onboard_team.py` do the whole job.
- [ ] **"What do I do next?" on the landing page.** The site reports state (47 of 87 evaluated); an SE opening it wants the actionable inverse - which epics still need a 2TS decision, which have no capability, which are blocked on something unresolved. Same data, different framing.
- [ ] **Constrain `Blocking Issues` input.** It is hand-typed free text with a comma-splitting hazard that has already caused one bug and one phantom node. Whether Smartsheet can constrain it without losing the qualifier syntax (`epic-x (Embedded, soft) [guess]`) is unknown - investigate before committing to it. The validator covers the symptom in the meantime.
- [ ] **Link the example render from the landing page.** It has been orphaned since progress went non-zero - the zero-progress note was the only thing that ever linked it, so today it is reachable only by typing the URL.

## Capability layer: the prak-v-model read path

The capability id, title and priority come from `capreq-*.md` frontmatter in
`asirobots/prak-v-model`. The capability's issue link is **Jama** as of
2026-09-05 — see *Jira retirement* below.

- [x] ~~**Set the `VMODEL_READ_TOKEN` repo secret**~~ Done 2026-08-27. The
      scheduled refresh now checks out `asirobots/prak-v-model` and regenerates
      the capability cache from source. Verified by A/B dispatch: run
      `33106528297` (secret unset) logged `note: .../.vmodel not checked out ...
      may be stale` and raised the "capability source unavailable" notice; run
      `33107998379` (secret set) logged `capability source checked out at
      .vmodel`, raised no such notice, and committed nothing — correct, because
      the cache already matched `prak-v-model` `main`.

      > **⚠ EXPIRES Wed 16 Sep 2026.** `friday github_review — brief` is a
      > 30-day token issued 17 Aug 2026. On expiry the checkout starts failing,
      > `continue-on-error` masks it, and **the job stays green** — the only
      > signal is the notice and job summary from the "Did the capability source
      > land?" step. Treat that date as a decision point, not a renewal chore:
      > regenerating this token invalidates it wherever Friday uses it (its
      > value is held server-side by the claude.ai connector and cannot be read
      > back), so the better move is minting the dedicated `prak-v-model` +
      > Contents:Read PAT below.

      **Decision 2026-08-26: reuse the existing `friday github_review` PAT.**
      Accepted with eyes open, after the two tighter options were ruled out:

      | Option | Outcome |
      |--------|---------|
      | Read-only deploy key | **Blocked.** asirobots disables deploy keys by org/enterprise policy — HTTP 422 "Deploy keys are disabled for this repository". Enabling them is a global policy change, not a repo-admin toggle. Do not retry this. |
      | New narrow PAT (`asirobots` owner, prak-v-model only, Contents:Read) | Viable, needs an ASI approval round. Deferred, not rejected. |
      | Reuse `friday github_review` | **Chosen.** Works today, no approval. Read access to `prak-v-model` confirmed 2026-08-26 — both the Contents permission and the repository scope. |

      Two known, accepted consequences:

      1. **Blast radius.** That PAT carries read on actions, discussions,
         issues, merge queues, pages and pull requests across asirobots — far
         more than the `Contents:Read` this job uses — and it now sits in a
         *public* repo's secret store. Anyone who gains write on this repo can
         read all of it. Fork PRs cannot reach it (no `pull_request` trigger),
         so the exposure is write-access-to-this-repo, which today is one
         person.
      2. **Lifecycle coupling.** Rotating or revoking it for the review tooling
         breaks this job. Because the checkout is `continue-on-error`, that
         would degrade the refresh to cached capability labels *silently* — so
         the "Did the capability source land?" step was added to post a
         `::notice::` and a job-summary warning when the checkout does not
         produce `.vmodel/product/requirements/product`.

- [ ] **Narrow `VMODEL_READ_TOKEN` to a dedicated Contents:Read PAT.** Follow-up
      to the decision above. **Do this by 16 Sep 2026**, when the shared token
      expires — that is the natural moment, since the alternative is
      regenerating a token other tooling depends on. Nothing in the workflow
      changes — same secret name, same `token:` input — so this is a pure
      credential swap. Resource owner must be `asirobots`, not the personal
      account; getting that wrong yields a 404 that reads like a typo'd repo
      name. Verify with a *Contents* call, not a repo call: `gh api
      repos/asirobots/prak-v-model/contents/product/requirements/product` should
      return 15 entries — `gh api repos/asirobots/prak-v-model` succeeds on
      Metadata alone and proves nothing.

      Placement, if ever redone: the secret belongs on
      **`pjm-autonomous/prak-sysreq-mgmt`** (the repo whose workflow *runs*),
      under *Settings > Secrets and variables > **Actions***, never on
      prak-v-model and never under the Agents tab — Agents secrets are for
      Copilot coding-agent sessions and are invisible to `${{ secrets.* }}` in a
      workflow run.

- [x] ~~**Delete `data/shared/capability-jira.json`** and
      `merge_capability_jira()`.~~ Done 2026-09-05, ahead of the trigger that
      was written here — not because `jira-key` landed upstream, but because the
      Jira layer it pointed at is being retired. Replaced by
      `capability-jama.json` + `merge_capability_jama()`.

## Jira retirement — capability links moved to Jama

ASI DevOps now syncs Jama `User Story` to Jira `Story` for sprint tracking, with
the story-to-System-Requirement relationship held in Jama. Jira **Epics,
Objectives and Initiatives are designated for removal**, which takes out both
Jira layers this repo referenced: the Initiative behind each capability tile, and
the Epic behind each tracker row's `Jira Key`.

Confirmed 2026-09-05: that relationship is exposed **only in Jama**, with no
machine-readable path out. The repo therefore does not model the story layer at
all — it stays at the System Requirement level, which is what it already was.

### Done 2026-09-05

- [x] ~~`feat/capreq-jira-key` deleted~~ (was `f897410` in `prak-v-model`,
      unpushed, plus a stale worktree). Its 10 lines were all Jira Initiative
      keys; merging it would have written dead keys into the source of record.
- [x] ~~Capability tiles and the landing-page capability table repointed to
      Jama~~ via `data/shared/capability-jama.json`. All 15 capabilities are
      listed, not the 9 that had a Jira Initiative — Jama is the requirements
      system of record, so every capreq exists there.
- [x] ~~`Jira Key` decoupled from the build.~~ Moved out of `COLS` into
      `OPTIONAL_COLS`, and `load_csv` now materialises every column so an absent
      one reads `""` rather than raising a `KeyError`. Verified: a tracker with
      no `Jira Key` column at all builds — 87 epics, same edges, same
      capabilities. The build no longer depends on the Jira deletion date.

### Open

- [ ] **Fill in the 15 Jama item ids** in `data/shared/capability-jama.json`.
      Every build names the slugs still missing one. Until then the tiles render
      the `CAP-nn` chip with no link — which is correct, since the Jira link they
      used to carry is dead. Obtainable via jama-mcp (Claude desktop app; the
      Claude Code extension does not have it).
- [ ] **Add `jama-id` to capreq frontmatter upstream**, then delete
      `capability-jama.json` — the reader already prefers frontmatter, so this is
      a data change with no code change. Same retirement path the Jira map took.
- [ ] **Repoint the tracker's `Jira Key` column at Jira Stories.** Plan of
      record: once stories exist in Jama/Jira and are synced, `Jira Key` carries
      the Story key on **child rows**. Note the generators read epic rows only,
      so a story-level `Jira Key` is not rendered by anything today — decide
      whether epic rows keep a key at all, or the column becomes purely
      informational.
- [ ] **Decide what happens to the tracker's story rows.** Once Jama is
      authoritative for stories, the tracker's 375 child rows and Jama's User
      Stories both claim to be "the stories for this sysreq", with no sync
      between them. They are not inert: they drive `Duration` -> `Story Points`
      -> the epic roll-up.
- [ ] **Re-key the sheet formulas off `JiraType`.** `Story Points` and `ManDays`
      branch on `JiraType@row = "Epic"`, an issue type that will not exist.
      `NumChildren@row > 0` is structural and says the same thing.


## ODOA / GNC / Mobius - registered, not onboarded

Containers exist and the registry knows them; nothing else does.

| | ODOA | GNC | Mobius |
|---|---|---|---|
| Jira project | `ODOA` (ODOA Platform) | `GNC` (GNC Platform) | `MP` (Mobius Platform) |
| PRAK epics in Jira | none yet | none yet | none yet |
| Smartsheet tracker | none | none | none |
| Container | `data/odoa/`, `agile-planning/odoa/` | `data/gnc/`, `agile-planning/gnc/` | `data/mobius/`, `agile-planning/mobius/` |

- [ ] Decompose each scope through [WORKFLOW.md](WORKFLOW.md) steps 1-11 and import the epics to Jama and Jira.
- [ ] Stand up each team's Smartsheet tracker from the shared template (steps 12-14), then set `sheet_id`, `sheet_url`, and `refresh: True` in that team's entry in `tools/teams.py`. Nothing else needs editing - the snapshot path, output directory, and agenda path all derive from the slug.
- [ ] Write each team's `agile-planning/<slug>/standingagenda.*` once the epic count and cadence are known.
- [ ] **`ODOA-5527` is already named as a blocker** in the Embedded-Core tracker. It renders as an external node under *other tracker* today; once ODOA has a snapshot it resolves to a real epic with a title and Jira link. Confirm the id is right before the ODOA decomposition starts.

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
`Blocking Issues`. It renders as an **external node** rather than resolving, since
`Blocking Issues` only resolves ids within its own sheet. External nodes are drawn
for context and excluded from the referencing team's counts.

### Done 2026-08-18

- [x] Tracker created and populated: 15 epics, capability + priority + Jira keys.
- [x] Jira keys filled: project `ET`, `ET-2951`..`ET-2965`. Each epic's Jira parent independently confirms its capability - 15/15 agree with the capability resolved through `prak-v-model`.
- [x] Capability tiles link to their shared Jira Initiative parent.
- [x] `tools/teams.py` registry added; both generators read it. `--team embedded` / `--team electronics` replace the long per-team command lines.
- [x] **Fixed a silent edge-dropping bug.** `Blocking Issues` entries of the form `epic-x (Embedded, soft) [guess]` were split on the comma inside the qualifier list, producing garbage refs that then failed to resolve and were discarded. All 9 Electronics dependencies would have rendered as zero edges while the output looked healthy.
- [x] Cross-team blockers now render as external nodes instead of being dropped, labelled with the other team's title and Jira link via `--cross-reference` (passed automatically by `--team`).
- [x] Provisional `[guess]` dependencies are parsed, labelled **guess** on the edge, and counted separately in the header.

### Still open

| Need | Why | Who |
|------|-----|-----|
| Confirm the 9 provisional dependencies | Every recorded edge is tagged `[guess]` - a working assumption, not a meeting decision. Until confirmed the Electronics critical path is indicative only. | Electronics evaluation meeting |
| Electronics meeting RACI | The agenda carries `TBD` for the SME, capacity, and 2TS-consulted roles. Embedded roles do not carry over automatically. | Patrick + Clint Jones |
| Evaluate the 15 epics | `2TS Required` is `TBD` on all 15. | Electronics evaluation meeting |

## Embedded-Core

- [ ] Populate `Blocking Issues` in the tracker during the evaluation meetings. Until then the real DAG renders 0 edges across all 87 epics.
- [x] ~~Commit the scheduled refresh workflow.~~ Done: `.github/workflows/refresh-dag.yml` is tracked and runs three times each weekday (07:00 / 12:00 / 17:00 Mountain), looping over `python3 tools/teams.py --refreshable`.
- [ ] Add the `SMARTSHEET_ACCESS_TOKEN` repo secret. This is a Smartsheet **personal API token**, not the Claude Connector — the runner is headless and calls the REST API directly, so the connector cannot stand in for it. Blocked on IT ticket #help00004986, and the account that would mint it is not provisioned yet, so treat this as open-ended. Until it lands the scheduled run **skips the tracker pull and carries on** rather than failing: it emits a `::notice::`, writes a "Tracker pull skipped" job summary, rebuilds from the committed snapshots, and titles any resulting commit *Rebuild dependency DAGs from capability metadata* so `git log` never claims a tracker read that did not happen. Changed 2026-08-26 — a red X every weekday is how a scheduled job teaches everyone to ignore it.
- [x] ~~Reconcile 40 unmapped tracker rows.~~ Done 2026-08-18: the tracker's `Initiative` column was renamed to `Capability` and all 87 rows populated with capreq slugs. All 87 now map to one of 9 capabilities (CAP-01 through CAP-09), and the unassigned group is gone.
- [ ] 40 of the 87 tracker rows still have no matching epic file in `prak-v-model/agile-planning/epics/` (47 rows do; 68 epic files exist, 21 of them for other teams). The capability grouping no longer depends on those files, so this is a v-model completeness question, not a DAG blocker.
- [x] ~~Reconcile the tracker against Jira.~~ Done 2026-08-18: Jira holds 93 PRAK-labelled epics against the tracker's 87. The 6 extras are MCHTRNCS-132, -136, -198, -201, -204 and one more, all `Platform Team` GNC or Perception. The tracker is correctly scoped to VSP-Embedded; 87 is right, not short by 6.
- [x] ~~Decide whether the committed snapshot should be a full-fidelity export.~~ Decided 2026-08-18: keep it to the generator columns. The other 9 are meeting scratch space (`Batch`, `2TS Rank`, `Story Titles`, `Owner`, ...) and this repo is public. `tools/export_snapshot.py` writes exactly those 7 from the live sheet.

## Blocked on access

- [ ] **Smartsheet API token.** Patrick's permission level excludes API keys. IT ticket **#help00004986**, submitted 2026-08-18. Until it lands, `--live` and `tools/export_snapshot.py` cannot run, and the scheduled refresh workflow cannot work even once it is committed. **Working path meanwhile:** in Smartsheet, File > Export > Export to CSV, then rebuild from the export: ```bash python3 tools/build_dependency_dag.py --team electronics --csv path/to/export.csv python3 tools/build_index.py ``` Committing the refreshed `data/<team>/tracker-snapshot.csv` keeps the published site current, since Pages rebuilds on every push. Ask IT for: a Smartsheet API access token (Personal Settings > API Access) with read on sheets `7348278000570244` and `2558444740497284`, issued under **`c00236@contractor.asirobots.com`**.
- [x] ~~**GitHub Actions workflow creation.**~~ Resolved: the `workflow` OAuth scope was granted and `.github/workflows/refresh-dag.yml` is committed and tracked. It still needs `SMARTSHEET_ACCESS_TOKEN` as a repo secret to do anything - see the entry above.

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
- Two generator defects found and fixed, both silent: `Blocking Issues` entries
  were split on commas inside qualifiers (would have shown 0 edges for all 9
  Electronics dependencies), and unresolvable refs were dropped rather than
  drawn (made cross-team dependencies invisible).
- One wrong finding recorded and corrected: "Electronics epics do not exist in
  Jira" came from a JQL scoped to `project = MCHTRNCS`; they are in `ET`.
- GitHub Pages enabled and verified live.

## Repo hygiene

- [x] ~~Commit and push.~~ Done 2026-08-18.
- [x] ~~Add a `CLAUDE.md`.~~ Done 2026-08-18, updated 2026-08-26 for the five-team container layout: records the shared-capability model, the hard rules (nothing hand-drawn, never commit raw exports to this public repo), the layout, the full rebuild sequence, and the conventions that are easy to get wrong.
- [x] ~~Turn on GitHub Pages.~~ Done - the site is live at https://pjm-autonomous.github.io/prak-sysreq-mgmt/.
- [ ] `data/prak_jira_snapshot-20260818.csv` is gitignored, not pruned. If the Jira export should be committed in some form, prune it to the used columns first: of its 508 columns only 58 carry data, and three of those are ECR field templates embedding internal labor rates.
