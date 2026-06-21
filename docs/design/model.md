# Design: Canonical Document & Schema Model

**Status:** Implemented (v0.1.1a1) — `import dataspec`, with the implementation in `dataspec.canonical`
**Date:** 2026-06-21
**Superseded:** the former `Doc` (dict/list/scalar) and `Type` tree (`ObjectType`/`ArrayType`/`ScalarType`/`RefType`/`AnyType`), removed in v0.1.1a1

---

> The model is **inspired by** Lee & Cheung, *"XML Schema Computations"*
> (CIKM 2010) — but you don't need the paper to read this. The definitions
> below are self-contained and use plain terms (node, edge, label, value,
> field, cardinality, scalar).

## 1. Summary

This defines dataspec's two core models — the **Document** (the data) and the
**Schema** (the constraint) — as one small, format-independent formalism,
deliberately restrictive for the JSON family of formats.

The headline ideas:

1. A **Document is an ordered list of labeled edges**, not a map whose values may be arrays.
2. A **Schema has exactly three building blocks** — `record` (constrained by its child labels), `Scalar` (one of seven fixed kinds, optionally nullable), and `Ref` (naming and recursion). A field's type is always exactly one `Scalar` or one `Ref` — never a composition of either.
3. **Field cardinality `[min,max]`** is the single mechanism for optional / required / array. There is no separate array type.
4. The model is **restrictive by default**: records are closed, scalar types are never composed into enums or unions, and the structureless escape hatches (`Any`, open objects, maps) are removed.

---

## 2. Motivation

The previous model accreted three problems:

- **The Document couldn't faithfully represent all inputs.** XML may interleave repeated elements (`<member/><other/><member/>`); a dict-with-array-values (`{"member": […], "other": …}`) has already reordered reality and cannot express the interleaving. The Document is supposed to be *canonical regardless of format*, but it was JSON-shaped.

- **One idea was fragmented across three mechanisms.** "How many times may this label appear, and what shape?" was split into a per-field `required` flag, array length bounds, and an open-map `rest` attribute — three shards of one idea, which is why each felt ad hoc and why `rest` was the source of a real soundness bug in `compatible_with`.

- **Structureless escape hatches undercut the tool's purpose.** `Any`, open objects, and the `[string]: T` map all let a schema declare "no structure here," which is the opposite of what a schema is for.

The redesign collapses the three shards into one (`cardinality`), gives the Document a canonical form that represents every input faithfully, and removes the escape hatches.

A later simplification also removed composed value types (enums and unions) from
field types entirely. The reason: if a field's type can be a composition of several
candidate representations — say, "either an integer or the literal string `unlimited`" —
then a value that happens to match more than one candidate (or none cleanly) leaves no
principled way to pick which Python type to materialize it as when deserializing. A
field's type is now always exactly one fixed scalar kind (optionally nullable) or one
`Ref` to a record, so there's never a choice to make.

---

## 3. Goals and non-goals

**Goals**
- One canonical Document model, format-independent, faithful to every supported input (including XML interleaving).
- A small, self-contained schema model that's restrictive by default — a schema guarantees structure.
- A clean formal definition both models can be specified and reasoned about from.

**Non-goals (deliberately deferred)**
- **Maps / open key sets** (`{ [string]: T }`). Removed for now; reintroduce later as an explicit, opt-in construct if needed.
- **Wildcard / open records** and **`Any`** — removed; they abandon structure.
- **Structural unions** (`{a}|{b}`), **value-domain unions/enums** (`"a" | "b"`), and **positional tuples** (`[string, integer]`) — not expressible; removed/deferred.
- **Constrained scalars** (e.g. `Email = string matching …`) — no value refinements yet.
- **Order-sensitive fields** — validation is order-free (see §4, §7).

---

## 4. Document model

A Document is a **node**: either a scalar value, or an ordered list of labeled edges.

```
value   = scalar  (string · integer · number · boolean · date · time · datetime)  |  null
edge    = (label: String, target)            where target = value | node
node    = [ edge, edge, … ]                  -- ordered; labels MAY repeat
Document = node                              -- (or a bare value at a leaf)
```

**Properties**

- **"Many" is a repeated label.** An array of `Member`s is the label `member` occurring N times — not a field pointing to an array. JSON `{"member":[A,B]}` and XML `<member>A</member><x/><member>B</member>` both become `[(member,A), …, (member,B)]`.
- **Object and array unify.** A node is just an ordered edge list; the object-vs-array distinction vanishes.
- **Order is preserved in the Document** (it is the canonical, faithful record) but is **data, never a schema constraint** (§7). A reordered round-trip remains schema-valid.

**Format mapping**

| Source | Document |
|---|---|
| JSON object `{"a":1,"b":2}` | `[(a,1),(b,2)]` |
| JSON keyed array `{"m":[A,B]}` | `[(m,A),(m,B)]` |
| YAML mapping / sequence | as JSON |
| TOML table / array-of-tables | as JSON |
| XML elements (incl. interleaved) | `[(tag,…),…]`, order preserved |

---

## 5. Schema model

A **Schema** is `(root, env)`, where `root` is a `Ref` and `env` maps names to **record definitions**. There is exactly one definition kind: a **record**, which constrains a node by its child labels. A field's type is either a `Scalar` (one of seven fixed kinds, optionally nullable) or a `Ref` to a named record — never a composition of several candidates.

```
Schema      = root: Ref ;  env: Name ⇀ Record

Record  = { Field… }                         -- CLOSED: only these labels
Field   = (label: String, type: Type, cardinality: [min, max])
Type    = Scalar | Ref(Name)                 -- exactly one scalar kind, or a named record

Scalar  = (kind, nullable: bool)             -- kind ∈ { string, integer, number, boolean, date, time, datetime }
          -- exactly one of the seven fixed kinds; never composed with another kind or a literal value
```

**Rules**

- **Records are closed.** Any label not named by a field is invalid. (No wildcard.)
- **Cardinality is the *only* mechanism for multiplicity** — how many times a label may appear, order ignored: `[1,1]` required (default), `[0,1]` optional, `[0,∞]` array, `[1,∞]` non-empty array, `[2,5]` bounded. **There is no separate Array type** — array-of-record is `cardinality > 1` with a `Ref` item.
- **`?` applies to scalars only.** `string?` is a nullable `Scalar{string}`. It **cannot** apply to a `Ref`. "This record may be absent" is `cardinality [0,1]`, never `?` (see §6).
- **Records are always named and reached by `Ref`.** No inline/anonymous records — this makes the schema a graph of named definitions (so reuse and recursion are uniform), not a nested tree.
- **A `Scalar` is exactly one fixed kind, optionally nullable — never composed.** No enums, no literal values in type position, no combining two kinds.

**Surface syntax** (shorthands desugar to the model)

```
record Member {
    "name": string,                  -- Scalar{string}
    "role": string,
}
record Team {
    "name":         string,
    "members" [0,]: Member,          -- cardinality [0,∞]; Ref(Member)
    "lead" [0,1]:   Member,          -- optional
}
root Team
```

- **Quoting rule:** `"quoted"` = a **data string** (a field label); an **unquoted identifier** = a **schema name** (a scalar kind or a `Ref`).
- `string?`, `integer?`, etc. are the nullable form of a scalar — the only suffix the grammar allows.
- `record` is the one naming keyword. ("type" is *not* a keyword — it would be ambiguous between "a definition", "the thing being named", and a record.)

---

## 6. Two deliberate exclusions

Two things the model intentionally cannot express, and why:

- **A record-or-null field.** A field's type is *either* a scalar *or* a `Ref` to a record — never both at once. "This value is a string or null" is a nullable scalar (`string?`); "this subtree is a Manager record or a bare null" would need a type that is half scalar and half `Ref`, which the model doesn't allow. So `?` (which makes a *scalar* nullable) applies only to scalars, and "this record might not be here" is expressed by **cardinality `[0,1]`** (the field may be absent) — not by a nullable reference.
- **Maps / open key sets.** A record names every label it allows. An open-ended key set ("any string key, all of type T") would be a structureless hole, so it's deferred (§3). Use a named record when the keys are known; for genuinely open data, this is a future, opt-in feature.

---

## 7. Conformance (validation)

A node `n` conforms to a `Record R` iff:
1. **Cardinality** — for each field `(label, type, [m,k])`, the count of edges in `n` with that label is in `[m,k]`.
2. **Closedness** — every edge label in `n` is some field of `R`.
3. **Targets** — each matching edge's target conforms to that field's `type`.

A value conforms to a `Scalar` iff it matches the scalar's kind (or is `null` and the scalar is nullable). A target conforms to `Ref(N)` iff it conforms to `env[N]`.

**Order is ignored.** Cardinality counts edges; it never constrains their sequence. A JSON document and an interleaved XML document with the same edges (in any order) conform identically.

---

## 8. Serialization (Document → format)

Group all edges sharing a label into one key, regardless of position: `[(m,A),(x,X),(m,B)]` → `{"m":[A,B], "x":X}`. Within-label order (`A` before `B`) is preserved; cross-label interleaving is dropped (no JSON-family format can express it). See §10 (1) for the count-1 rule.

---

## 9. Impact on the current implementation

This is a **breaking redesign of the core**, not an incremental change:

- **Document representation** changes from `dict`/`list`/scalar to an ordered edge list. The `Doc` API (`get`/`child`/`add`/…) would be reframed as a projection over edges; array access becomes "collect same-label edges."
- **Type tree** is replaced: `ObjectType`+`ArrayType` collapse into `Record` (fields with cardinality); `ScalarType` becomes `Scalar` (one fixed kind, optionally nullable, never composed); `AnyType` is removed; `RefType` stays.
- **Codecs** change: readers build edge lists; writers group by label and consult cardinality (or a fallback) to choose array-vs-bare.
- **DSL** changes: quoted-label rule, the `record` keyword, `[m,n]` cardinality, `?` scalar-only.
- **Operations** (`validate`/`compatible_with`/`equivalent`/`normalize`) re-expressed on the new model — and several get *simpler* (no `rest` special-casing; a scalar check becomes "is this value's set a subset of the other's").

A phased path is possible (introduce the edge-list Document behind the existing API first, then the schema model), but the end state is incompatible with today's public types.

---

## 10. Resolved decisions

The corner cases, and how they're settled (all implemented):

1. **Count-1 serialization → schema-driven, with an always-list fallback.** When a schema is available, cardinality decides array-vs-bare (`max > 1` → list, else bare) — faithful, idiomatic output. With no schema, fall back to always-list (every grouped label becomes an array). This keeps the Document format-independent (no format-derived bits) and puts the array/bare decision where the cardinality actually lives.
2. **Array-of-scalar → a repeated label**, uniform with array-of-record (`"tags"[0,]: string`). One mechanism (cardinality) for all "many," matching XML's repeated elements.
3. **Bare nested arrays (`[[1,2],[3,4]]`) → forbidden for now.** Inner elements have no label, so there's no edge to give them (and XML can't express them either); reading one raises a clear error. Revisit only if a concrete need appears.
4. **Root → a `Ref` to a single record (single-rooted).** Guarantees a lossless XML round-trip (one document element) and keeps the entry point uniform with every other definition.

---

## Appendix: worked example

Schema:

```
record Member {
    "name": string,
    "role": string,
}
record Team {
    "name":         string,
    "members" [0,]: Member,
}
root Team
```

Document (canonical edge list) for a two-member team:

```
[ ("name", "Platform"),
  ("member", [ ("name","Ann"), ("role","dev") ]),
  ("member", [ ("name","Bob"), ("role","pm")  ]) ]
```

- JSON projection: `{"name":"Platform", "members":[{"name":"Ann","role":"dev"},{"name":"Bob","role":"pm"}]}`
- XML projection: `<name>…</name><member>…Ann…</member><member>…Bob…</member>` (and an interleaved XML input round-trips through the *same* Document).
- Conformance: `member` occurs twice ∈ `[0,∞]` ✓; each `member` target conforms to `Member` ✓; `name` once ∈ `[1,1]` ✓; no unlisted labels ✓.
