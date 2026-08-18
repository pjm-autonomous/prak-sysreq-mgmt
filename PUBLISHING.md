# Publishing & release

How the PRAK epic-decomposition pages get in front of people. Three delivery
surfaces, one build. Read [CLAUDE.md](CLAUDE.md) first for the two-team model and
the hard rules (nothing hand-drawn, never commit raw exports to this public repo).

| Surface | What it is | When to use | Mermaid mode |
|---------|-----------|-------------|--------------|
| **GitHub Pages** | The live site, rebuilt on every push to `main` | The default. Stakeholders get a durable URL that tracks the trackers. | `vendor` (default) |
| **Self-contained file** | One `.html` that renders with no siblings and no network | Email an attachment, drop in a shared drive, hand to someone offline | `inline` |
| **claude.ai Artifact** | A page hosted on claude.ai, shareable to teammates | A snapshot for a review or a message thread, no repo access needed | `inline` |

The tracker data is identical across all three. Only *how the viewer loads
Mermaid* changes, and that is one flag: `--mermaid`.

---

## 1. GitHub Pages (the live site)

**Live:** https://pjm-autonomous.github.io/prak-sysreq-mgmt/

Pages is configured `build_type: legacy` — it serves `main` at repo root and
GitHub rebuilds it itself on every push. **No GitHub Actions workflow is involved
in publishing**, so the missing `workflow` OAuth scope (see
[TODO.md](TODO.md)) does not block it. Push to `main`, the site updates.

Because the site is same-origin, the DAG viewers reference the committed
`vendor/mermaid.min.js` by a relative path (`--mermaid vendor`, the default when
the bundle exists). No CDN, no runtime third-party dependency.

### The refresh loop (manual, until the Smartsheet token lands)

`--live` and `tools/export_snapshot.py` need a Smartsheet API token that
Patrick's account cannot yet mint (IT ticket **#help00004986**). Until then the
release loop is manual but small:

```bash
# 1. In Smartsheet: File > Export > Export to CSV, for each sheet you changed.
#    Embedded  -> sheet 8066207570677636
#    Electronics -> sheet 5660443916849028

# 2. Rebuild that team's snapshot + DAG from the export. This overwrites the
#    committed data/tracker-snapshot*.csv with only the 7 generator columns,
#    so no raw export (account ids, labor rates) ever reaches the public repo.
python3 tools/build_dependency_dag.py --team electronics --csv ~/Downloads/export.csv

# 3. Rebuild the landing page LAST — it counts from the snapshots.
python3 tools/build_index.py

# 4. Commit the regenerated products and push. Pages redeploys from here.
git add data/ agile-planning/ index.html
git commit -m "Refresh Electronics DAG from tracker export"
git push -u origin <branch>
```

Once the API token exists, steps 1–2 collapse into
`python3 tools/export_snapshot.py --team <x>` +
`python3 tools/build_dependency_dag.py --team <x>`, and
`.github/workflows/refresh-dag.yml` can run the whole thing on a schedule (it
needs the `SMARTSHEET_ACCESS_TOKEN` repo secret and the `workflow` scope to be
committed — both still open in TODO.md).

> **Never hand-edit `index.html` or anything under `agile-planning/*/`.** They are
> build products and the next regenerate overwrites them. Fix the tracker or the
> generator instead.

---

## 2. Self-contained single file (`--mermaid inline`)

A `vendor`-mode page is *not* portable on its own: it points at
`../../vendor/mermaid.min.js`, and if that sibling is missing it falls back to a
jsdelivr CDN import — which needs network and is blocked in a claude.ai Artifact.
So for anything that leaves the site, embed the bundle:

```bash
python3 tools/build_dependency_dag.py --team electronics \
  --mermaid inline \
  --outdir /tmp/share --basename prak-electronics-dag
```

The result is a single ~3.6 MB `.html` that:

- renders with **no sibling files and no network** — open it from a download
  folder, an email attachment, or a USB stick and the graph draws;
- keeps every interaction (search, filters, capability drill-down, zoom/pan);
- carries the same "generated `<timestamp>`" stamp, so the reader knows its age.

The `inline` cost is the 3.6 MB weight, which is why the committed site does
**not** use it — regenerating inline files after every meeting would churn git
history with a 3.6 MB blob each time. Generate inline copies **outside the repo**
(e.g. `/tmp`) on demand; don't commit them.

---

## 3. claude.ai Artifact

claude.ai Artifacts run under a strict CSP that blocks external hosts, so the
CDN fallback cannot fire. **You must publish the `inline` build**, not a
`vendor` or `cdn` one — otherwise the viewer loads but the graph silently stays
blank.

1. Generate the inline file (section 2 above).
2. Publish it as an Artifact. It renders self-contained; the embedded bundle sets
   `globalThis.mermaid` and the page's own `mermaid.run()` draws every panel, so
   the graph, drill-down, and zoom all work inside the Artifact sandbox.
3. Share the Artifact link. Artifacts start **private**; the recipient sees it
   only after you share it.

Note: Artifacts also render Mermaid natively from `<pre class="mermaid">` blocks,
but this viewer ships its own loader and does far more than draw a diagram
(filters, inventory, pan/zoom). Publish the whole inline page — do not try to
reduce it to a bare Mermaid block.

Because a page cannot call Smartsheet from inside the sandbox, an Artifact is a
**snapshot**, not a live view. "Refreshing" one means regenerating the inline
file and republishing it to the same Artifact URL.

---

## Release checklist

Before you push a refresh or hand out a file:

- [ ] Snapshots regenerated from the **current** export, not edited by hand.
- [ ] `build_index.py` re-run **after** the DAGs, so the landing-page counts and
      the diagrams describe the same read.
- [ ] Only pruned derivatives committed — `git status` shows no raw
      `prak_jira_snapshot-*.csv` or full Smartsheet export (both are gitignored;
      confirm nothing slipped in).
- [ ] The "generated" timestamp on each DAG viewer reflects this build.
- [ ] For a shared file or Artifact: built with `--mermaid inline`, opened once
      with the network **off** to confirm the graph still draws.
- [ ] Pushed to the designated branch; Pages redeploy confirmed at the live URL.

## Mermaid modes, in one place

`--mermaid` accepts:

| Mode | Behavior | Portable? | Repo weight |
|------|----------|-----------|-------------|
| `auto` *(default)* | `vendor` if `vendor/mermaid.min.js` exists, else `cdn` | — | none |
| `vendor` | relative `<script src>` to the committed bundle | same-origin only | none |
| `inline` | embeds the 3.6 MB bundle in the file | **yes, fully** | 3.6 MB/file |
| `cdn` | imports from jsdelivr at view time | needs network + reachable CDN | none |

Update the vendored bundle with the one-liner in
[vendor/README.md](vendor/README.md); the version there must stay in sync with
the file.
