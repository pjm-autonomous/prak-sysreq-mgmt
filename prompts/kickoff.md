# Reusable prompts

Copy-paste prompts for the [sysreq decomposition workflow](../WORKFLOW.md).
Replace every `{{placeholder}}` before sending.

## Kickoff prompt

Paste into Claude Code at the start of a decomposition run.

```
# PRAK sysreq decomposition — kickoff
Scope: {{SYSREQ_DOMAIN}}        # e.g. Embedded, GNC, Electronics
Team slug: {{TEAM_SLUG}}        Jama project: {{JAMA_PROJECT}}
Jira filter: PRAK_beta_v1-allItems (#22297)
V-model checkout: {{VMODEL_PATH}}
DAG repo: pjm-autonomous/prak-sysreq-mgmt

Work the sysreq decomposition workflow for the scope above, pausing for my
sign-off where marked [SIGN-OFF]:

1.  Verify the integrity of the {{SYSREQ_DOMAIN}} system requirements; list gaps
    and inconsistencies before proceeding.
2.  Inspect the architecture and correct references down the chain
    (sysreq -> capability -> use case).
3.  Regenerate prak-v-model/TRACEABILITY.md; summarize what changed. [SIGN-OFF]
4.  Run the checks in prak-v-model/.github/workflows/ci.yml locally and
    confirm they pass.
5.  Prepare the Jama import: {{jama-import-workbooks | jama-mcp payload}}.
6.  Present the prepared Jama items for my review.             [SIGN-OFF]
7.  On my go, import to Jama via {{jama-mcp | CSV}}.
8.  Prepare the Jira import with the jira-import skill.
9.  Present the prepared Jira items for my review.             [SIGN-OFF]
10. Hand me the Jira CSV + steps to import (you can't write to Jira).
11. Cross-check: ingest fresh Jama & Jira exports and diff against the
    repo; report every mismatch as an adversarial reviewer.   [SIGN-OFF]
14. Hand off for tech review, then confirm the tracker's Claude Connector is
    enabled so refreshes reach the DAGs. (Numbering matches WORKFLOW.md;
    12-13 below are one-time and skipped on updates.)

# One-time when onboarding a new team (skip on updates):
# 12. Create the Smartsheet tracker from the template.
# 13. Branch the DAG repo, add a {{TEAM_SLUG}} entry to tools/teams.py.
```

## Refresh prompt

Paste after a tracker update to republish the DAGs (see
[Publishing an update](../WORKFLOW.md#publishing-an-update)).

```
Pull the latest {{SYSREQ_DOMAIN}} Smartsheet tracker via the connector,
refresh the DAG viewers and landing page, commit, and push to main.
```
