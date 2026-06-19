# Writing a format plugin

A **format** in dataspec is just three functions — `read`, `write`, `check` —
registered under a name. The four built-ins (JSON, YAML, TOML, XML) are
implemented exactly this way and register themselves on import; a third-party
format is no different, and needs no change to dataspec itself.

## What you implement

A plugin is a [`Format`](api.md#format-registry):

```python
from dataspec import Format

Format(
    name="csv",                 # the string callers use: Doc.from_format("csv", ...)
    read=read_csv,
    write=write_csv,
    check=check_csv,
    extensions=(".csv",),       # optional — informational, not enforced
    requires=(),                 # optional — third-party deps, for error messages
)
```

Three callables, each over **plain Python** — never `Doc` directly:

- **`read(text: str) -> Document`** — parse a string into a Document (a
  `dict` / `list` / `str` / `int` / `float` / `bool` / `None` / `datetime`
  tree). Raise `ParseError` if `text` isn't valid in your format, or falls
  outside whatever subset you support.

- **`write(data, *, strict=False, report=None, **opts) -> str`** — serialize a
  Document to a string. Must accept (and honor) `strict` and `report`, even if
  your format never needs to adjust anything — see
  [The adjustment-report contract](#the-adjustment-report-contract) below.
  `**opts` is yours: any keyword arguments specific to your format (TOML's
  `wrap_key`, for instance).

- **`check(data, **opts) -> WriteReport`** — simulate `write` and return only
  the report, producing no output. In practice this means factoring your real
  serialization logic into a private helper that both `write` and `check`
  call, the same way every built-in does (e.g. `_serialize_toml`).

That's the whole contract. `read`/`write`/`check` are plain functions — there's
no base class to subclass and no required imports beyond the error types you
raise.

## The adjustment-report contract

Not every format can hold every Document losslessly — TOML and XML have no
`null`; JSON has no `datetime`. Rather than silently dropping information or
raising on the common case, a writer **adjusts** the data to fit and records
what it changed in a [`WriteReport`](api.md#reading-and-writing-formats) of
[`Adjustment`](api.md#reading-and-writing-formats)s. This is what gives callers
the lenient/inspect/strict choice:

```python
write_toml(doc)                  # lenient (default): adjust, return output
write_toml(doc, report=rep)       # same, but rep now lists every change
check_toml(doc)                   # the report only, no output
write_toml(doc, strict=True)      # raise WriteError if anything was adjusted
```

If your format can hold every Document as-is (no nulls problem, no missing
types), your report is always empty and `strict` never fires — that's a valid,
simple plugin. If it can't, factor your real logic into a helper that returns
`(text, WriteReport)`, and hand the `strict`/`report` decision to
[`finish_write`](api.md#reading-and-writing-formats) — the same helper every built-in
writer uses internally:

```python
from dataspec import WriteReport, finish_write

def write_csv(data, *, strict=False, report=None, **opts):
    text, rep = _serialize_csv(data, **opts)   # your real logic, returns (str, WriteReport)
    return finish_write(text, rep, strict=strict, report=report)

def check_csv(data, **opts):
    _text, rep = _serialize_csv(data, **opts)
    return rep
```

`finish_write(text, rep, *, strict=False, report=None)` merges `rep` into
`report` if given, raises `WriteError(str(rep), report=rep)` if `strict` and
`rep` has any adjustment (any severity), and otherwise returns `text`
unchanged — there's no need to reimplement that decision yourself.

Inside `_serialize_csv`, call `rep.add(path, code, message, severity)` for
every adjustment, where:

- `path` is a `$`-prefixed path matching validation-error style (`"$.items[3]"`).
- `code` is a stable, machine-checkable string (`"null.field.omitted"`).
- `severity` is `"warning"` (conventional, recoverable) or `"error"` (likely
  to surprise — e.g. dropping a `null` array item, which shifts positions).
  `strict` raises on *any* adjustment regardless of severity; severity is
  advice for a human reading the report, not a strictness threshold.

## A worked example

A `csv` format that only supports a flat array of single-level objects (the
common "list of records" shape), and has to adjust when given anything else —
nested values, for instance, get stringified rather than silently dropped:

```python
import csv
import io
from typing import Any

from dataspec import Format, ParseError, WriteReport, WriteError, finish_write, register_format


def read_csv(text: str) -> Any:
    rows = list(csv.DictReader(io.StringIO(text)))
    if not rows and text.strip():
        raise ParseError("CSV has a header but no data rows")
    return rows


def _serialize_csv(data, **_opts):
    rep = WriteReport()
    if not isinstance(data, list) or not all(isinstance(r, dict) for r in data):
        rep.add("$", "shape.unsupported",
                "CSV needs a list of flat objects; got something else", "error")
        return "", rep

    fieldnames = sorted({k for row in data for k in row})
    out = io.StringIO()
    writer = csv.DictWriter(out, fieldnames=fieldnames)
    writer.writeheader()
    for i, row in enumerate(data):
        clean = {}
        for k, v in row.items():
            if isinstance(v, (dict, list)):
                rep.add(f"$[{i}].{k}", "value.stringified",
                        "nested value has no CSV representation; stringified", "warning")
                v = str(v)
            clean[k] = v
        writer.writerow(clean)
    return out.getvalue(), rep


def write_csv(data, *, strict: bool = False, report: WriteReport = None, **opts) -> str:
    text, rep = _serialize_csv(data, **opts)
    return finish_write(text, rep, strict=strict, report=report)


def check_csv(data, **opts) -> WriteReport:
    _text, rep = _serialize_csv(data, **opts)
    return rep


register_format(Format("csv", read_csv, write_csv, check_csv, (".csv",), ()))
```

## Registering and using it

`register_format` is the entire registration step — call it once (e.g. at
import time of your plugin module) and the format is usable everywhere:

```python
from dataspec import Doc, formats

"csv" in formats()                                          # True
Doc.from_format("csv", "name,age\nAnn,30\n").to_data()       # [{"name": "Ann", "age": "30"}]
Doc.from_data([{"name": "Ann"}]).to_format("csv")            # "name\r\nAnn\r\n"
```

`register_format` replaces any existing format of the same name — there's no
separate "unregister"; register again to override.

## Testing your plugin

Mirror the pattern dataspec's own tests use for a registered format
(`tests/test_registry.py`): register it, then exercise `read`/`write`/`check`
directly and through `Doc`:

```python
def test_csv_round_trips_flat_records():
    register_format(Format("csv", read_csv, write_csv, check_csv, (".csv",)))

    rows = [{"name": "Ann", "age": "30"}]
    text = write_csv(rows)
    assert read_csv(text) == rows

def test_csv_reports_nested_data():
    rep = check_csv([{"name": "Ann", "address": {"city": "London"}}])
    assert rep.warnings and not rep.errors    # adjusted, not fatal

    with pytest.raises(WriteError):
        write_csv([{"name": "Ann", "address": {"city": "London"}}], strict=True)
```

## Checklist

- [ ] `name` is unique (registering an existing name replaces it silently).
- [ ] `read` raises `ParseError` — not a bare exception — on invalid input.
- [ ] `write` accepts `strict` and `report` and ends with `finish_write(...)`
      (even if your format never adjusts anything).
- [ ] `check` returns the same report `write` would produce, without output.
- [ ] Every adjustment has a stable `code` and the right `severity`.
- [ ] `extensions` and `requires` are set if relevant (informational only —
      dataspec doesn't validate file extensions or auto-install dependencies).
- [ ] A test registers the format and exercises `read`/`write`/`check` plus
      `Doc.from_format`/`to_format`.

See [Formats](formats/overview.md) for how the built-in formats use this same
mechanism, and the [API reference](api.md#format-registry) for the exact
`Format`, `WriteReport`, and `Adjustment` signatures.
