# TOML

Reading uses the standard-library `tomllib` (Python 3.11+); writing needs
`pip install tomli_w`.

```python
from omnist import read_toml, Doc

d = Doc(read_toml("""
[order]
id = "A1"
[[order.items]]
sku = "W"
[[order.items]]
sku = "G"
"""))
d.to_json()    # '{"order": {"id": "A1", "items": [{"sku": "W"}, {"sku": "G"}]}}'
```

## How it maps

- A table becomes a list of edges; nested tables (`[a.b]`) nest.
- An **array-of-tables** (`[[order.items]]`) is the idiomatic array of records —
  it maps to a repeated `items` label, the same as JSON `"items": [{…}, {…}]`.

## Notes

- **No `null`.** TOML has no null value, so writing one is lenient by default:
  the edge is dropped and recorded as a `null.omitted` adjustment (a warning).
  `write_toml(node, report=rep)` shows it; `strict=True` raises `WriteError`
  instead. See [adjustment reports](../api.md#adjustment-reports-lossy-writes).
- **Top-level must be a table.** A bare scalar or array at the root isn't valid
  TOML; a single-rooted Document (one top-level key) writes cleanly.
- TOML has native date, time, and datetime types, which read straight into the
  matching scalar kinds.
