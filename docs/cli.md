# CLI

The `omnist` command-line tool — a thin wrapper over the library described
throughout the rest of these docs; every command maps directly onto one or
two calls into the public `omnist` API. This page documents exactly what's
implemented today; the full planned command surface is
[the CLI spec](design/cli-spec.md).

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
