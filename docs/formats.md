# Formats: the Data Tree as a canonical hub

The **Data Tree** is a format-neutral model of a data *instance*; the
**Schema Automaton** is the format-neutral model of a *schema*. Concrete
serialization syntaxes — JSON, YAML, TOML (and, later, XML) — are **codecs**
around these canonical models.

```
   JSON ─┐                                   ┌─ JSON
   YAML ─┼─ load ─►  Data Tree  ─► emit ─────┼─ YAML
   TOML ─┘        (canonical model)          └─ TOML
```

Transcoding is therefore just *load one syntax, emit another*:

```python
from src import tree_from_json, to_toml

toml_text = to_toml(tree_from_json('{"name": "Ann", "tags": ["x", "y"]}'))
```

## Loaders (syntax → Data Tree)

| Function | Needs |
|----------|-------|
| `tree_from_json(text)` | stdlib |
| `tree_from_yaml(text)` | `pyyaml` |
| `tree_from_toml(text)` | stdlib `tomllib` (3.11+) or `tomli` |
| `tree_from_python(obj)` | — (already-parsed `dict`/`list`/scalar) |

## Emitters (Data Tree → syntax)

| Function | Needs |
|----------|-------|
| `to_json(tree, *, indent=None, sort_keys=False)` | stdlib |
| `to_yaml(tree, *, sort_keys=False)` | `pyyaml` |
| `to_toml(tree)` | `tomli_w` |
| `tree_to_python(tree)` | — (the hub; reconstructs a typed Python value) |

`tree_to_python` is the inverse of `tree_from_python` and the basis for all the
emitters.

## Type fidelity

Each scalar d-node carries a `vdom` **type hint** set by the loader, so values
survive a round-trip with their type intact:

```python
to_json(tree_from_python({"age": 30, "zip": "999"}))
# {"age": 30, "zip": "999"}      # 30 stays a number, "999" stays a string
```

A tree built by hand (no hints) falls back to a best-effort interpretation of the
string value.

## The canonical model is the JSON data model

The hub models record / list / scalar over **string · number · bool · null**.
Each target syntax is a *projection* of it, and they do not all cover the same
ground:

| Target | Coverage | Notes |
|--------|----------|-------|
| **JSON** | full | the reference data model |
| **YAML** | full | superset of JSON; `null`, any top-level value |
| **TOML** | **partial** | **no `null`**; the **top level must be a table** (object) |

When a tree cannot be represented in the target syntax, the emitter raises
`SerializationError` with the offending path — it never emits invalid output:

```python
to_toml(tree_from_python({"x": None}))
# SerializationError: TOML has no null value; cannot serialize null at $.x.

to_toml(tree_from_python([1, 2, 3]))
# SerializationError: TOML documents must have a table (object) at the top level; got list.
```

These are real differences between the formats' data models, not bugs — JSON and
YAML accept both of those documents.

## Where XML fits

XML is structurally different (ordered children, attributes, mixed text), so it
is **not** a projection of the JSON data model. Supporting XML as another codec
is the motivation for making list/record addressing first-class in the model —
see [Design & Limitations](design-and-limitations.md). For now the hub covers the
modern JSON-family syntaxes; XML is a planned codec.

## Example: a config converter

```python
from src import tree_from_json, to_toml, to_yaml

config_json = '''
{
  "service": "api",
  "port": 8080,
  "tls": {"enabled": true, "ciphers": ["A", "B"]}
}
'''
tree = tree_from_json(config_json)
print(to_toml(tree))   # emit the same config as TOML
print(to_yaml(tree))   # ...or YAML
```

See [demos/08_format_hub.py](../demos/08_format_hub.py) for a runnable tour.
