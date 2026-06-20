# Changelog

All notable changes to this project are documented here. The format is loosely
based on [Keep a Changelog](https://keepachangelog.com/); this project is
**alpha** and the public API may still change between releases.

## [v0.1.0a4]

A security/robustness audit of the format codecs, prompted by the
question "is the library safe now?" Found and fixed five more real
bugs, none caught by the edge-case sweep in v0.1.0a3:

- Fixed: a small, ordinary YAML payload using anchors/aliases to share
  structure (not a cycle, just YAML's normal way of avoiding
  duplication) took time **exponential** in nesting depth to validate
  — a 469-byte, 9-level payload that `yaml.safe_load` parses instantly
  didn't finish validating in 15 seconds. The cause was dataspec's own
  post-parse cycle/depth check re-walking a shared subtree once per
  alias reference instead of once per unique object; PyYAML itself
  shares the constructed objects and was never the problem. Now linear
  in the number of unique objects.
- Fixed: `read_xml` silently fell back to the standard library's XML
  parser (vulnerable to XXE/entity-expansion) with no indication at
  all when the optional `defusedxml` dependency isn't installed. Now
  raises `UnsafeXMLWarning` each time this happens.
- Fixed: `read_json`/`read_toml` leaked the underlying parser's native
  exception (`json.JSONDecodeError`, `tomllib.TOMLDecodeError`) on
  malformed input instead of wrapping it in `ParseError` like
  `read_yaml`/`read_xml` already did, breaking the documented
  "catch everything with `except ParseError`" contract.
- Fixed: `write_xml` embedded literal control characters (e.g. a NUL
  byte) directly in the output with no warning — unlike the format's
  other adjustments, this isn't lossy, the result doesn't parse as XML
  *at all*. Now stripped and reported as `string.illegal_xml_char`,
  an error.
- Fixed: `infer()` crashed with a raw `AttributeError`/`TypeError` on a
  sample like `[False, {}]`, instead of the same clean, documented
  `SchemaError` every other "mix of structure and scalar" sample
  already got. A bool was classified separately from other scalars in
  the structural-mixing check; now it isn't.
- New: `tests/test_property.py` — property-based fuzzing with
  `hypothesis`, generating randomized Documents and text across every
  codec and the DSL parser on every CI run. Found three of the five
  bugs above.
- New: `SECURITY.md` — the trust model for each format (what's
  hardened, what isn't) and how to report a vulnerability (GitHub
  private vulnerability reporting, now enabled on this repo).

## [v0.1.0a3]

- Fixed: deeply/adversarially nested input (`Doc` construction, the
  functional `write_*`/`read_*` codecs, and the schema DSL parser) used
  to crash with an uncatchable `RecursionError`; each now raises a clean
  `DocumentError`/`SchemaError` past a depth limit.
- Fixed: a real key collision (e.g. JSON's `{1: "a", "1": "b"}`, or two
  XML keys sanitizing to the same element name) was reported as a soft
  warning even though it silently overwrites one value with the other;
  now reported as `key.collision`, an **error**.
- Fixed: the format registry (`register_format`/`get_format`/`formats()`)
  was an unsynchronized global dict; a plugin registered from a
  background thread could race a concurrent lookup. Now thread-safe.
- Fixed: three more silent XML/TOML data-corruption cases found by a
  systematic edge-case sweep — a string that looks like a number/bool/
  `null` silently changing type on read (`string.ambiguous`), an empty
  object/array silently becoming an empty string or vanishing entirely
  (`container.empty.ambiguous`), an integer beyond TOML's signed 64-bit
  range written without warning (`integer.out_of_range`), and a string
  containing `\r` silently losing its line endings per the XML spec's
  own normalization rules (`string.line_ending_normalized`). All four
  are now reported, and rejected by `strict=True`.
- New: `tests/edge_cases.py` / `tests/test_edge_cases.py` — a shared
  corpus of ~45 edge-case values swept across every format and a few
  API operations (`Doc`, `infer`, DSL round-trip) via general
  invariants rather than hand-coded expectations per case.
- New: `tests/test_dsl.py` negative-path coverage — one case per
  distinct `SchemaError` the hand-written DSL parser can raise.
- CI now runs `ruff check .` and every `examples/*.py` script, not just
  `pytest`.
- New: `CONTRIBUTING.md`.
- Removed the redundant `sys.path.insert` boilerplate from every
  example and test file (the editable install already covers it); a
  few `pyproject.toml` metadata fields filled in.

## [v0.1.0a2]

- New: `finish_write(text, rep, *, strict=False, report=None)`, a public
  helper format plugins can call instead of reimplementing the
  strict/report decision every built-in writer makes; the built-ins
  (`write_json`/`write_yaml`/`write_toml`/`write_xml`) now use it too.
- New: [`docs/plugins.md`](docs/plugins.md) — a guide for writing a format
  plugin (the `Format` contract, the adjustment-report pattern, a
  verified worked example, testing, and a checklist).
- Project practices: `CHANGELOG.md`, `ruff` lint config, a `py.typed`
  marker (PEP 561), and branch protection on `master` requiring CI.
- Changes from here on go through a pull request rather than a direct
  commit to `master`.
- Docs: example city/coordinates data changed from Hong Kong to London
  (and Shenzhen to Dublin); assorted doc-accuracy fixes found during a
  full pass over the doc set (stale TOML array-formatting comments, a
  missing validation error, clarified empty-array inference).

## [v0.1.0a1] - first tagged alpha

- Core model: `Doc` (the guarded data-DOM) and the `Schema`/`Type` tree
  (`ScalarType`, `ArrayType`, `ObjectType`, `AnyType`, `RefType`).
- Schema DSL: `parse_schema` / `to_dsl`, plus a Python schema builder
  (`obj`, `arr`, `mapping`, `enum`, `optional`, `nullable`, `ref`, `schema`,
  and the `t` namespace for scalar atoms).
- Pluggable format registry with built-in JSON, YAML, TOML, and XML codecs
  (`read_*` / `write_*` / `check_*`), lenient by default with adjustment
  reporting (`WriteReport` / `Adjustment`) and an opt-in `strict` mode.
- `infer()` to draft a schema from example Documents.
- Schema comparison operations: `compatible_with`, `equivalent`, `normalize`.
- Full exception hierarchy under `DataspecError`.
- GitHub Actions CI running the test suite (228 tests) on Python 3.11–3.13.
- Complete documentation set: concepts, architecture, getting started, the
  `Doc` API, the schema language, format-by-format pages, inference, schema
  comparison, an API reference, and an FAQ — every code example verified
  against the library.
