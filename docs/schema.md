# Schemas

A **schema** describes the shape a Document is allowed to have. You write one in
a small text language, parse it with `parse_schema`, and call `validate` on a
[`Doc`](document.md):

```python
from dataspec import parse_schema, doc

schema = parse_schema("root { name: string, age: integer }")
schema.validate(doc({"name": "Ann", "age": 30})).ok    # True
```

> Validation is **Doc-only** — wrap your data with `doc(...)` (or read it with
> `Doc.from_json(...)`) first. The examples below assume `doc` is imported.

You can also build the same schema in Python instead of as text — see
[The Python builder](#the-python-builder). This page defines every concept and
every type, with examples.

## Concepts

A Document is built from three kinds of values, and a schema has a type for each.

**Scalar** — a single, indivisible value: a piece of text, a number, a boolean,
or a date/time. `"Ann"`, `30`, `3.14`, `true`, and `2024-01-01` are all scalars.

**Array** — an ordered list of values that all share one type, like
`[1, 2, 3]` or `["a", "b"]`. Position matters; the values are homogeneous.

**Object** — a collection of named fields, where each key is a string and each
value is itself a Document: `{"name": "Ann", "age": 30}`. This is a Python
`dict`. An object can also be used as a **map** — arbitrary keys that all share
one value type (see [Maps](#maps)).

On top of those, two ideas apply everywhere:

**Nullability** — whether a position may also hold `null` (Python `None`). It is
not a separate type; any type can be made nullable by adding `?`.

**Named types** — a reusable, possibly self-referencing type you define once and
refer to by name. This is how you describe trees and other recursive shapes.

## The schema text

A schema is one `root` declaration plus any number of named types:

```
type Address = { street: string, city: string }

root {
    name:    string,
    address: Address,
}
```

- `root T` declares the type of the whole document. Exactly one is required.
- `type Name = T` defines a named type. Order doesn't matter — you can refer to
  a type before it's defined.
- `#` starts a comment that runs to the end of the line.

## Scalar types

| Keyword | Matches |
|---------|---------|
| `string` | text |
| `integer` | whole numbers (not booleans) |
| `number` | integers or floats (not booleans) |
| `boolean` | `true` / `false` |
| `date` | a calendar date |
| `time` | a time of day |
| `datetime` | a date and time |

```python
parse_schema("root string").validate(doc("hi")).ok       # True
parse_schema("root integer").validate(doc(5)).ok          # True
parse_schema("root integer").validate(doc(5.5)).ok        # False (not whole)
```

A few deliberate rules:

- **`integer` is a `number`, but not vice versa.** `5` satisfies both;
  `5.5` satisfies only `number`.
- **Booleans are never numbers.** In Python `True == 1`, but a schema treats
  `boolean` and `integer`/`number` as distinct so you don't accidentally accept
  `true` where you wanted a count.
- **Dates may arrive as text.** JSON and XML have no date type, so a date is
  usually a string like `"2024-01-01"`. The `date`, `time`, and `datetime` types
  accept both real `datetime` objects and ISO-8601 strings, so the same schema
  validates data whether it came from TOML (native dates) or JSON (ISO strings).

## Enums and unions

A **union** lists alternatives with `|`. For scalars this widens what's allowed:

```
root integer | string        # an integer OR a string
```

An **enum** is a union of specific string values — the data must be exactly one
of them:

```
root "open" | "shipped" | "cancelled"
```

> Unions are for scalars and enums. You can't union two different *structures*
> (say, two different object shapes) — see [Limitations](#limitations).

## Nullable types

Add `?` to allow `null` as well. It works on any type:

```
root string?                      # a string or null
root { user: { name: string }? }  # the user object may be null
root [integer]?                   # the whole array may be null
```

`string?` and `string | null` mean the same thing.

## Arrays

`[T]` is an array whose every item has type `T`. You can also constrain the
length:

| Syntax | Meaning |
|--------|---------|
| `[T]` | zero or more |
| `[T]+` | one or more |
| `[T]{n}` | exactly `n` |
| `[T]{m,n}` | between `m` and `n` |
| `[T]{m,}` | at least `m` |
| `[T]{,n}` | at most `n` |

```
root {
    tags:   [string],          # any number of strings
    scores: [number]+,         # at least one
    coords: [number]{2},       # exactly two (e.g. [lon, lat])
}
```

Arrays are **homogeneous**: all items share one type. To allow mixed scalars,
use a union as the item type — `[integer | string]`.

## Objects

An object lists its fields. A field is **required** by default; add `?` to the
*name* to make it optional:

```
root {
    name:  string,      # required
    age?:  integer,     # optional
}
```

By default an object is **closed** — unexpected keys are an error. End the field
list with `...` to make it **open**, allowing extra keys with any value:

```
root { id: string, ... }     # id is checked; any other keys are allowed
```

```python
s = parse_schema("root { a: integer }")
s.validate(doc({"a": 1, "b": 2})).ok          # False — 'b' is unexpected

s = parse_schema("root { a: integer, ... }")
s.validate(doc({"a": 1, "b": 2})).ok          # True
```

## Maps

Often an object is used as a **map**: the keys aren't known ahead of time, but
every value has the same type — like `{"2024-01": 5, "2024-02": 8}`. Write that
with an index signature, `[string]: T`:

```
root { [string]: integer }          # any string keys -> integer values
```

```python
s = parse_schema("root { [string]: integer }")
s.validate(doc({"jan": 1, "feb": 2})).ok      # True
s.validate(doc({"jan": "x"})).ok              # False — values must be integers
```

You can combine known fields with a map for the rest:

```
root {
    version: integer,           # a known field
    [string]: number,           # every other key maps to a number
}
```

The value type can be anything, including objects and arrays:

```
root { [string]: { lat: number, lon: number } }    # a map of points
```

## The `any` type

`any` matches any Document at all, including `null`. Use it for a field whose
contents you don't want to constrain:

```
root { id: string, payload: any }
```

Use it sparingly — `any` turns off checking for that position. (An open object,
`{ ... }`, is just an object whose extra values are `any`.)

## Named and recursive types

Define a type once and reuse it; a type may refer to itself, which is how you
describe trees:

```
type Tree = {
    value: integer,
    kids:  [Tree],
}
root Tree
```

```python
s = parse_schema("type Tree = { value: integer, kids: [Tree] }\nroot Tree")
s.validate(doc({"value": 1, "kids": [{"value": 2, "kids": []}]})).ok   # True
```

A reference to an undefined type is caught when you parse the schema:

```python
parse_schema("root { a: Missing }")      # raises SchemaError: unknown type 'Missing'
```

## Validation results

`validate` returns a `ValidationResult`:

- `result.ok` — `True` if the document fits.
- `bool(result)` — same as `.ok`, so `if result:` works.
- `result.errors` — a list of failures. Each is an `Error` with `.path` (a
  location like `$.items[0].id`) and `.message`. It also unpacks as
  `(path, message)`.
- `print(result)` — a readable multi-line summary.

```python
r = parse_schema("root { items: [{ id: integer }] }").validate(doc({"items": [{"id": "x"}]}))
r.errors[0].path        # '$.items[0].id'
r.errors[0].message     # 'expected integer, got string'
```

## Round-tripping a schema to text

`schema.to_dsl()` (or `to_dsl(schema)`) prints a schema back as DSL text — handy
for showing an inferred schema or saving one to a file. Parsing that text gives
back an equivalent schema.

## Limitations

- **No structural unions.** You can union scalars (`integer | string`) and enum
  values, but not two different object or array shapes. If you need
  "either this object or that one," model it as one open or `any`-valued object,
  or validate the variants separately.
- **Arrays are homogeneous.** There's no fixed-length, mixed-type tuple such as
  `[string, integer, boolean]`. Use a union item type for mixed scalars, or an
  object with named fields when each position has a distinct meaning.
- **Map keys are always strings.** That matches JSON/YAML/TOML/XML, where object
  keys are strings.

## The Python builder

You don't have to use the text language. The builder constructs the *same* schema
object tree from Python expressions — handy when a schema is generated or
composed, where string concatenation would be awkward, and friendlier to IDEs and
type checkers.

```python
from dataspec import (
    schema, obj, arr, mapping, enum, optional, nullable, ref,
    string, integer, number, boolean, date, time, datetime, any,
)

s = schema(obj(
    name    = string,
    age     = optional(integer),               # an optional field
    status  = enum("open", "shipped"),         # a fixed set of values
    tags    = arr(string),                      # an array
    deleted = nullable(boolean),                # also accepts null
    scores  = mapping(integer),                 # a map { [string]: integer }
))
```

The vocabulary:

| Builder | Produces | DSL equivalent |
|---|---|---|
| `string`, `integer`, `number`, `boolean`, `date`, `time`, `datetime` | a scalar type | the same keywords |
| `any` | matches anything | `any` |
| `obj(**fields)` | a closed object | `{ ... }` |
| `optional(t)` | marks a field not-required | `name?: t` |
| `nullable(t)` | a type that also accepts null | `t?` |
| `arr(item, min=, max=)` | an array (optionally bounded) | `[item]{min,max}` |
| `mapping(t)` | a map of string keys to `t` | `{ [string]: t }` |
| `enum(*values)` | a fixed set of literals | `"a" \| "b"` |
| `ref(name)` | a named-type reference | `Name` |
| `schema(root, **named)` | assembles a `Schema` | `root … type Name = …` |

For a scalar **union** use the class directly: `ScalarType({INTEGER, STRING})`
(the same as `integer | string`).

Named types and recursion work by passing named types to `schema(...)` and
referring to them with `ref`:

```python
node = obj(value=integer, kids=arr(ref("Node")))
s = schema(ref("Node"), Node=node)             # type Node = { value, kids: [Node] }
```

The builder produces ordinary `ObjectType` / `ScalarType` / … objects, which you
can also navigate with uniform getters: `obj_type.field("name")`,
`obj_type.children()`, `array_type.item`, `object_type.rest`. See the
[API reference](api.md#schema-builder).
