# Sysreq decomposition workflow

How one system-requirement scope — Embedded, GNC, Electronics, and so on — travels
from an integrity check to Jama, Jira, and the published dependency DAGs.

This is the SE-team process behind this repo. A visual version is maintained as a
Claude artifact; this file is the shareable source of record. See also
[PUBLISHING.md](PUBLISHING.md) for how the pages are released and
[CLAUDE.md](CLAUDE.md) for the two-team model and hard rules.

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
| **Claude Code** _(added)_ | With the `jama-import-workbook` and `jira-import` skills available. |
| **V-model source** _(added)_ | `prak-v-model` checked out for capability / use-case traceability, and the sysreq scope agreed. |

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
   regenerated `TRACEABILITY.md` links and signs off before anything is imported.
4. **Confirm CI will pass** — _Claude Code._ Run the checks in `CI.yml` locally so
   the branch is green before import.

### C. Prepare & import to systems of record

5. **Prepare the Jama import** — _Claude Code._ Either generate the Jama import
   workbook (`jama-import-workbook`), or prepare the payload for the Jama MCP.
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
    `prak-sysreq-mgmt`, add the new team directory, and expand the dependency-DAG
    scope to cover it.

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

A hands-off scheduled refresh is possible later — it needs a `SMARTSHEET_ACCESS_TOKEN`
repo secret plus the refresh workflow committed. See [PUBLISHING.md](PUBLISHING.md)
and [TODO.md](TODO.md).

## Iterating

For every later change, loop back through steps **1–11** and **14**. Skip the
one-time setup: **12–13** run only when a team is first onboarded.

---

Reusable prompts live in [prompts/kickoff.md](prompts/kickoff.md).
