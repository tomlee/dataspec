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
