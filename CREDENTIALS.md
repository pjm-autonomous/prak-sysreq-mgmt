# Credentials

Four different things authenticate to two different services, and two of them
share the word "token". Getting them confused cost real time three separate
times, so this is the map.

## The four

| Credential | Reaches | Used by | Lives in |
|---|---|---|---|
| **Smartsheet Claude Connector** | Smartsheet sheets | An interactive Claude session | claude.ai connector settings, per user |
| **`SMARTSHEET_ACCESS_TOKEN`** | Smartsheet REST API | `export_snapshot.py`, `--live`, the scheduled refresh | `~/.bashrc` locally; repo secret for CI |
| **`VMODEL_READ_TOKEN`** | **GitHub** — `asirobots/prak-v-model` | The scheduled refresh's capability checkout | Repo secret only |
| **GitHub `gh` login** | This repo | You, pushing | `gh auth`, keyring |

**The connector and `SMARTSHEET_ACCESS_TOKEN` are not interchangeable.** They
reach the same data, but the connector authorises a human's interactive Claude
session while the token authorises a headless caller. A GitHub runner has no
Claude session, so the connector cannot stand in for the token — and the token
cannot be pasted into the connector, which has no field for it.

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
