# vendor

Third-party assets committed so the published pages have no runtime CDN dependency.

| File | Version | Source |
|------|---------|--------|
| `mermaid.min.js` | 11.16.1 | `https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.min.js` |

`mermaid.min.js` is the self-contained UMD build (it sets `globalThis.mermaid`),
not the ESM entry point, which imports separate chunk files and cannot be used
standalone.

The generator picks it up automatically: `--mermaid auto` (the default) uses this
file when it is present and falls back to the CDN when it is not. See
`tools/build_dependency_dag.py --help`.

To update, re-download to this path and change the version in the table above:

```bash
curl -sSL -o vendor/mermaid.min.js \
  https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.min.js
```
