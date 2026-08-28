# Sysreq decomposition workflow

How one system-requirement scope — Embedded, GNC, Electronics, and so on — travels
from an integrity check to Jama, Jira, and the published dependency DAGs.

This is the SE-team process behind this repo. A visual version is maintained as a
Claude artifact; this file is the shareable source of record. See also
[PUBLISHING.md](PUBLISHING.md) for how the pages are released and
[CLAUDE.md](CLAUDE.md) for the team-container model and hard rules.

**Legend.** Each step names who acts: **Human SE**, **Claude Code**, or an
**external system** (Jama / Jira / Smartsheet / GitHub). A **◆ sign-off** is a
required human gate that blocks everything after it. Steps marked **one-time** run
only when a team is first onboarded.

Published DAGs & progress: <https://pjm-autonomous.github.io/prak-sysreq-mgmt/>

---

## Before you start (prerequisites)

Have these in place for the scope you're decomposing. Items tagged _(added)_
weren't in the original list — prune if they don't apply to your team.

| Need | What |
|------|------|
| **Jama access** | The `jama-mcp` connector, or Round-Trip Export enabled on the Jama project. |
| **Jira export** | "Excel CSV (all items)" of filter **PRAK_beta_v1-allItems** (#22297): <https://asirobots.atlassian.net/issues/?filter=22297> |
| **Smartsheet** | An account with the **Claude Connector** enabled on the tracker. |
| **Repo access** | GitHub — or Claude-Code — write access to `pjm-autonomous/prak-sysreq-mgmt`. |
| **Claude Code** _(added)_ | With the `jama-import-workbooks` and `jira-import` skills available. |
| **V-model source** _(added)_ | `prak-v-model` checked out for capability / use-case traceability, and the sysreq scope agreed. |
| **Team slug** _(added)_ | A short lowercase slug (`embedded`, `electronics`, `odoa`, `gnc`, `mobius`). It names the team's container and every generated path. |

---

## The flow

### A. Requirements & architecture

1. **Verify requirements integrity** — _Human SE._ Confirm the system requirements
   in scope are complete and internally consistent. Work one sysreq domain at a
   time (Embedded, GNC, …).
2. **Inspect architecture & correct references** — _Claude Code._ Walk the
   architecture and fix references down the chain so each link resolves:
   sysreq → capability → use case.

### B. Traceability & CI

3. **Review the traceability matrix** — **◆ Human sign-off.** A human reads the
   regenerated `prak-v-model/TRACEABILITY.md` links and signs off before anything
   is imported.
4. **Confirm CI will pass** — _Claude Code._ Run the checks in
   `prak-v-model/.github/workflows/ci.yml` locally so the branch is green before
   import.

### C. Prepare & import to systems of record

5. **Prepare the Jama import** — _Claude Code._ Either generate the Jama import
   workbook (`jama-import-workbooks`), or prepare the payload for the Jama MCP.
6. **Validate before Jama import** — **◆ Human sign-off.** A human checks the
   prepared items and approves the import.
7. **Import to Jama** — _External system._ Write the approved items — by the Jama
   MCP (Claude), or by CSV upload (human).
8. **Prepare the Jira import** — _Claude Code._ Generate the Jira import with the
   `jira-import` skill. No MCP option — Claude cannot write to Jira.
9. **Validate before Jira import** — **◆ Human sign-off.** A human checks the
   prepared items and approves the import.
10. **Import to Jira** — _External system._ A human uploads the approved CSV to
    Jira — the only route, since Claude cannot write to Jira.

### D. Verify the import

11. **Cross-check imported items** — **◆ Human sign-off.** Human inspection of the
    imported items — and/or a Claude adversarial agent that ingests fresh Jama &
    Jira exports and diffs them against the repo, reporting any mismatch.

### E. Tracking & visualization _(one-time per team)_

12. **Create the Smartsheet tracker** — _Human SE, one-time._ Stand up the team's
    decomposition tracker from the shared template.
13. **Add the team to the DAG repo** — _Claude Code, one-time._ Branch
    `prak-sysreq-mgmt` and add one entry to `tools/teams.py` — name, title, Jira
    project, sheet id, sheet URL, `refresh: True`. The team's container
    (`data/<slug>/`, `agile-planning/<slug>/`) and every generator path derive
    from the slug, so nothing else needs editing.

### F. Review & connect

14. **Tech review & connect the tracker** — _Human (tech team) + Smartsheet._ The
    tech team reviews, then the Smartsheet is updated with the connector enabled so
    live refreshes flow into the DAGs.

---

## Publishing an update

**Updating the Smartsheet does _not_ refresh the DAGs on its own** — the published
site reads committed snapshots, not the live sheet. After any tracker change:

1. In a Claude Code session with the Smartsheet connector, ask it to **pull the
   latest tracker and refresh the DAGs**.
2. It rebuilds the snapshot, regenerates the DAG viewers and landing page, commits,
   and pushes to `main`.
3. GitHub Pages rebuilds in ~1–2 min — confirm at
   <https://pjm-autonomous.github.io/prak-sysreq-mgmt/>.

A hands-off scheduled refresh is already wired up: `.github/workflows/refresh-dag.yml`
is committed and runs three times each weekday - 07:00, 12:00 and 17:00
Mountain - committing any change it finds. The one
thing still outstanding is the `SMARTSHEET_ACCESS_TOKEN` repo secret — without it the
run skips the tracker pull, says so in a job summary, and rebuilds from the committed
snapshots. So the DAGs stay current with the capability layer, but the progress numbers
keep reflecting the last manual refresh until that secret lands.

**The Smartsheet Claude Connector does not cover that.** The connector authorizes a
human's interactive Claude session; the scheduled workflow runs headless on a GitHub
runner with no Claude session and calls the Smartsheet REST API directly with a
personal API token. Two separate credentials for two separate paths. The same applies
locally: `tools/export_snapshot.py` and `--live` always need the token, even in a
session where the connector is working. See [PUBLISHING.md](PUBLISHING.md) and
[TODO.md](TODO.md).

## Who changes what (access model)

**Only the repo owner has write access to `pjm-autonomous/prak-sysreq-mgmt`.**
That is deliberate, and it costs the other SEs nothing, because the repo is not
where their data lives.

GitHub cannot scope write access to a folder — repository permissions are
repo-wide, and rulesets restrict paths for everyone at once, not per person. The
per-team scoping we actually want already exists one layer up: **Smartsheet
shares per sheet.** So a team lead gets write on *their* tracker and no GitHub
access at all, and the scoping is enforced where it is enforceable.

> **Never hand-edit `data/<slug>/tracker-snapshot.csv`.** For a team with a live
> tracker the scheduled job runs `export_snapshot.py` over every entry with
> `refresh: True` and overwrites that file. A hand-edit — emailed CSV or merged
> PR alike — survives until the next scheduled run, at most a few hours, and
> then disappears. The
> PR route is the more dangerous of the two because it leaves a paper trail
> saying the change was reviewed and accepted, while the published page silently
> reverts.

Pick the route that matches the change:

### Route 1 — Tracker data (2TS decisions, blockers, capability grouping)

_Team SE. No GitHub access needed, no hand-off, no PR._

1. Edit your team's Smartsheet tracker. That is the source of truth.
2. Stop. Nothing else is required of you.
   - In a hurry? Comment **`/refresh`** on any issue in the DAG repo and the
     pages rebuild within a couple of minutes. Read access is enough - the
     workflow runs with the repository's permissions, not yours. You must be
     on `REFRESH_ALLOWLIST`; ask the owner to add you.
3. The scheduled refresh re-reads the sheet, regenerates the DAG and the landing
   page, and commits. See [Publishing an update](#publishing-an-update) for the
   timing and for what still needs a human today.

### Route 2 — Standing agenda

_Team SE. Fork and PR — read access is enough._

`agile-planning/<slug>/standingagenda.*` is the **only** hand-authored artifact
in the repo; everything else under `agile-planning/` is generated and would be
overwritten. Because the repo is public, an SE with no write access can still
contribute:

1. Fork `pjm-autonomous/prak-sysreq-mgmt` to your own account.
2. Edit `agile-planning/<your-slug>/standingagenda.html` and `.txt` on a branch.
3. Open a PR against `main`. Do not touch anything outside your team's folder.
4. Owner reviews and merges.

### Route 3 — Generator, tooling, or documentation fix

_Anyone. Fork and PR, same as Route 2._

Include what you ran to verify it. For a generator change that is the full
rebuild loop from [CLAUDE.md](CLAUDE.md#rebuilding-everything) plus confirmation
that the regenerated artifacts differ only where you intended.

### Route 4 — Onboarding a new team

_Owner, one-time._ Steps 12–14 above. Do not build a CSV hand-off pipeline as a
substitute for standing up the tracker: a snapshot committed for a team with
`sheet_id: None` does persist (nothing overwrites it), which makes it a workable
demo and a bad process — it removes the pressure to create the tracker, and it
is replaced wholesale the day one appears.

### Route 5 — Refreshing the published pages

_Owner._ Fully automatic once `SMARTSHEET_ACCESS_TOKEN` exists. Until then the
owner exports each changed sheet by hand — see
[Publishing an update](#publishing-an-update). The other SEs are not blocked on
this and are not involved in it; the owner has access to every tracker.

---

## Iterating

For every later change, loop back through steps **1–11** and **14**. Skip the
one-time setup: **12–13** run only when a team is first onboarded.

---

Reusable prompts live in [prompts/kickoff.md](prompts/kickoff.md).
