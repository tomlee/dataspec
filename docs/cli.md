# CLI

The `omnist` command-line tool — a thin wrapper over the library described
throughout the rest of these docs; every command maps directly onto one or
two calls into the public `omnist` API. This page matches
[the CLI spec](design/cli-spec.md) exactly.

## `omnist format`

```
omnist format <input> [-o OUTPUT]
```

Canonicalizes an OML document — `read_oml` then `write_oml`. `<input>` is a
file path or `-` for stdin; `-o`/`--output` is a file path, or omit it for
stdout.

```sh
omnist format messy.oml -o clean.oml
echo 'a:   1' | omnist format -
# a: 1
```

Malformed OML raises the same `ParseError` `read_oml` would, printed to
stderr as `error: ...`, exit code `2` — nothing written.

## `omnist convert`

```
omnist convert <input> --from FMT --to FMT [--schema FILE] [--strict] [--report] [--result-format text|json|oml] [-o OUTPUT]
```

`read_<from>(text, schema=...)` → `write_<to>(node, strict=, report=)`.
Reformats data across formats, optionally upgrading/validating it against
a schema on the way in (per the [deserialization guarantee](deserialization.md)).

`--from oml --to oml` is rejected (exit `2`, pointing at `omnist format`
instead) — that's the one same-format case with a real alternative.
Every *other* same-format pair (`json`→`json`, `yaml`→`yaml`, etc.) is
allowed through `convert`, since there's no replacement command for
those (other formats already have their own formatters elsewhere; this
CLI doesn't duplicate them).

If `--schema` is given and the input can't be made to conform,
`materialize` raises `ParseError` (every problem found, not just the
first) — printed to stderr, nothing written, exit `2`.

`--report` and `--strict` map directly to `write_<to>`'s own `report=`/
`strict=` parameters (no effect on `--to oml`, which never needs them —
OML is always exactly lossless):

- **`--report`** prints what got adjusted to **stderr** (`--result-format`,
  default `text`, controls the encoding — same `text`/`json`/`oml`
  convention as everywhere else) — the write still happens normally.
  `--result-format` without `--report` has no effect.
- **`--strict`** refuses to write at all if anything would need
  adjusting — exit `1` (a definite "no, not losslessly possible," grouped
  with `validate`/`compatible-with`'s `1`, not the usage/parse failures
  that exit `2`).

`convert` is one document in, one document out — no batch mode (the
library's `read_xml`/`write_xml` only support a single-rooted Document;
converting many files is a shell loop).

```sh
omnist convert order.json --from json --to oml
omnist convert order.xml --from xml --to oml --schema order.osd -o order.oml
cat data.toml | omnist convert - --from toml --to json

omnist convert data.json --from json --to toml --report -o data.toml
omnist convert data.json --from json --to toml --strict -o data.toml
```

## `omnist check`

```
omnist check <input> --from FMT --to FMT [--strict] [--result-format text|json|oml]
```

Reports what `write_<to>` would adjust (`check_json`/`check_yaml`/
`check_toml`/`check_xml`/`check_oml`) **without ever writing anything** —
`convert`'s dry-run counterpart, for asking the question without
producing (or risking producing) any output. Unlike `convert`,
`--from`/`--to` may be equal.

By default, `check` always exits `0` — it's purely informational.
`--strict` turns it into a CI gate: exit `0` if nothing would need
adjusting, `1` if anything would.

```sh
omnist check data.json --from json --to toml
omnist check data.json --from json --to toml --strict && echo "safe to convert losslessly"
```

## `omnist infer`

```
omnist infer <input>... --from FMT [-o OUTPUT]
```

All inputs must be the same format. Each is read as a `Doc`,
[`infer(docs)`](schema.md#operations-compare-and-infer) drafts a schema
from them, written out as OSD.

```sh
omnist infer samples/*.json --from json -o inferred.osd
```

## `omnist validate`

```
omnist validate <input> --from FMT --schema FILE [--result-format text|json|oml]
```

Reads `<input>` as `FMT` (`json`/`yaml`/`toml`/`xml`/`oml`) **without**
schema-directed upgrading — the same lenient parse a plain `read_<from>`
call would produce — then runs `Schema.validate` against the OSD file
given by `--schema`. This mirrors the library's own validation/
deserialization split: validation only ever *checks* a value already in
the document; it never converts anything (see [Schema-directed
deserialization](deserialization.md) for the upgrading side of that
split, which is what `convert --schema` does instead).

`--result-format` (default `text`) controls the printed result:

- `text` — `ValidationResult`'s own `"invalid:\n  at $.path: message"`
  formatting, or `valid`.
- `json` — `{"ok": bool, "errors": [{"path": str, "message": str}, ...]}`.
- `oml` — the same `{ok, errors}` shape, OML-encoded.

```sh
omnist validate order.json --from json --schema order.osd
omnist validate order.json --from json --schema order.osd --result-format json
```

Exit `0` if valid, `1` if invalid, `2` on a read/parse error (malformed
input or schema, printed to stderr as `error: ...`).

## `omnist schema format`

```
omnist schema format <schema-file> [-o OUTPUT]
```

Canonicalizes an OSD ([Omnist Schema Definition](schema.md)) file —
`parse_schema` then `to_dsl`. Same records, same names, just canonical
whitespace/field order; it never changes a schema's structure (contrast
[`Schema.normalize()`](schema.md#operations-compare-and-infer), which can
merge structurally-identical records).

```sh
omnist schema format messy.osd -o clean.osd
```

Malformed OSD raises `SchemaError`, printed to stderr as `error: ...`,
exit code `2`.

## `omnist schema normalize`

```
omnist schema normalize <schema-file> [-o OUTPUT]
```

`Schema.normalize()`, written back out as OSD — unlike `schema format`,
this *can* change a schema's structure (merging separately-named records
that are structurally identical).

```sh
omnist schema normalize messy.osd -o normalized.osd
```

## `omnist schema compatible-with`

```
omnist schema compatible-with <a> <b> [--result-format text|json|oml]
```

`a.compatible_with(b)` — true if every Document `a` accepts, `b` also
accepts (`b` is backward-compatible with `a`). `--result-format` (default
`text`) prints `true`/`false`, `{"compatible": bool}` (`json`), or the
same shape OML-encoded. Exit `0` if true, `1` if false, `2` on a parse
error.

```sh
omnist schema compatible-with v1.osd v2.osd && echo "safe to ship v2"
```

## `omnist schema equivalent`

```
omnist schema equivalent <a> <b> [--result-format text|json|oml]
```

`a.equivalent(b)` — true if both accept exactly the same Documents. Same
output/exit convention as `compatible-with`.
