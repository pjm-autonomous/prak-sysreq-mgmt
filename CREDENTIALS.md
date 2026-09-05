# Credentials

Four different things authenticate to two different services, and two of them
share the word "token". Getting them confused cost real time three separate
times, so this is the map.

## The four

| Credential | Reaches | Used by | Lives in |
|---|---|---|---|
| **Smartsheet Claude Connector** | Smartsheet sheets, as whichever account authorized it | An interactive Claude session | claude.ai connector settings, per user |
| **`SMARTSHEET_ACCESS_TOKEN`** | Smartsheet REST API | `export_snapshot.py`, `--live`, the scheduled refresh | `~/.bashrc` locally; repo secret for CI |
| **`VMODEL_READ_TOKEN`** | **GitHub** — `asirobots/prak-v-model` | The scheduled refresh's capability checkout | Repo secret only |
| **GitHub `gh` login** | This repo | You, pushing | `gh auth`, keyring |

## The Smartsheet account

**Everything is under `c00236@contractor.asirobots.com`** (userId
`4902286880204676`). It owns the `prak-sysreq-decomposition` workspace, both live
trackers, `prak-TEMPLATE-epics`, and the archived sheet. Both Smartsheet
credentials above must be that account.

**`patrick.mckee-cn47@contractor.asirobots.com` (userId `251541673273220`) is
dead.** It is the pre-2026-08-27-reconfiguration account. It still holds two
stale workspaces containing the superseded sheets `8066207570677636` and
`5660443916849028`, and it still carries Admin on `Embedded-Core Epic Decomp` —
which is the *only* reason a connector authorized as it can read that sheet at
all. Nothing should be authorized as this account.

### How to tell which account a credential is on

There is no whoami. Ask Claude to list Smartsheet workspaces:

| What comes back | Account |
|---|---|
| `prak-sysreq-decomposition` | `c00236` — correct |
| `PRAK Embedded-Core Epic Decomposition` + `PRAK Electronics Epic Decomposition` | `patrick.mckee-cn47` — wrong, re-authorize |

Sharpest single test: read `prak-electronics-epics` (`2558444740497284`). The
right account returns 15 epics; the dead one returns 403/404. Or read the sheet's
share list — it reports each grantee's email outright.

### Re-authorizing the connector onto `c00236`

Needed once; the grant is not tied to the browser tab, so opening Smartsheet
again changes nothing.

1. In a browser, sign in to `app.smartsheet.com` and confirm the account menu
   reads `c00236@contractor.asirobots.com`. Sign the other account out first if
   it appears — the OAuth step silently reuses whatever session is live, which is
   how the grant landed on the wrong account in the first place.
2. claude.ai → **Settings → Connectors** → Smartsheet → **Disconnect**.
3. **Connect** again, complete the OAuth prompt, approve access.
4. Verify: ask Claude to list workspaces and to read sheet `2558444740497284`.
   Expect `prak-sysreq-decomposition` and 15 Electronics epics.
5. Only after step 4 passes, remove `patrick.mckee-cn47` from the
   `Embedded-Core Epic Decomp` share list. Doing it earlier severs the current
   connector's access to the one sheet it can still read.

Claude cannot run step 2 or 3 — OAuth needs an interactive browser.

**The connector and `SMARTSHEET_ACCESS_TOKEN` are not interchangeable.** They
reach the same data, but the connector authorises a human's interactive Claude
session while the token authorises a headless caller. A GitHub runner has no
Claude session, so the connector cannot stand in for the token — and the token
cannot be pasted into the connector, which has no field for it.

**Neither says which Smartsheet account it is on, and that has already bitten.**
A connector authorized as the dead account read the Embedded tracker perfectly
while returning 403 on every other sheet — which reads exactly like a wrong sheet
id in `tools/teams.py`. Mint `SMARTSHEET_ACCESS_TOKEN` under `c00236` (Personal
Settings → API Access) and confirm the account before believing an access error.

**`VMODEL_READ_TOKEN` has nothing to do with Smartsheet.** It reads a GitHub
repository. It is named "token" and it lives beside a Smartsheet secret, which is
the whole reason this file exists.

## Where a repo secret goes

`Settings > Secrets and variables > `**`Actions`** on
`pjm-autonomous/prak-sysreq-mgmt` — the repo whose *workflow runs*. Never on
`prak-v-model`, and never under the **Agents** tab: those are for Copilot
coding-agent sessions and are invisible to `${{ secrets.* }}` in a workflow run.

```bash
gh secret set SMARTSHEET_ACCESS_TOKEN --repo pjm-autonomous/prak-sysreq-mgmt
gh secret set VMODEL_READ_TOKEN       --repo pjm-autonomous/prak-sysreq-mgmt
```

## Local setup

The generators read the environment, not a `.env` file. `~/.bashrc` is the place
— a non-interactive shell (which is what tooling runs in) sources nothing else:

```bash
printf '\nexport SMARTSHEET_ACCESS_TOKEN=%s\n' 'PASTE' >> ~/.bashrc
```

`prak-v-model` needs no credential locally; the sibling checkout is read directly.

## Expiry — the one that will bite

**`VMODEL_READ_TOKEN` expires Wed 16 Sep 2026.** It currently holds the shared
`friday github_review — brief` PAT, a 30-day token issued 17 Aug 2026.

On expiry the capability checkout fails, `continue-on-error` swallows it, and
**the job stays green**. The only signal is the `::notice::` and the "Capability
source unavailable" job summary from the *Did the capability source land?* step.

Treat that date as a decision point rather than a renewal: regenerating the shared
token invalidates it wherever Friday uses it, and Friday holds its value
server-side where it cannot be read back. The clean move is minting a dedicated
PAT — resource owner **`asirobots`**, `prak-v-model` only, **Contents: Read**.

## Verifying a GitHub PAT actually reads prak-v-model

```bash
GH_TOKEN=<pat> gh api repos/asirobots/prak-v-model/contents/product/requirements/product --jq 'length'
```

`15` means real access. **Do not** test with `gh api repos/asirobots/prak-v-model`
— that returns 200 on `Metadata: Read` alone and proves nothing about whether a
clone will work.

## What breaks without each

| Missing | Effect |
|---|---|
| `SMARTSHEET_ACCESS_TOKEN` | Scheduled refresh skips the tracker pull, rebuilds from committed snapshots, says so in the job summary, and titles any commit as a capability rebuild rather than a tracker refresh. |
| `VMODEL_READ_TOKEN` | Capability labels and Jira keys come from the committed cache in `data/shared/`. Job summary warns. |
| Both | The refresh is a no-op that commits nothing. Nothing is damaged. |

Neither is required for the published site to keep working — it serves committed
artifacts, and both failures degrade to "current data, slightly stale labels."
