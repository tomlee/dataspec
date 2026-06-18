# Schema Automaton

A Python implementation of the **Data Tree** and **Schema Automaton** models and
schema-computation algorithms from:

> Thomas Y. Lee & David W. Cheung,
> *"XML Schema Computations: Schema Compatibility Testing and Subschema
> Extraction"*, CIKM 2010.

…extended into a **data-format-agnostic** schema engine that can model and
validate the structure of **JSON, YAML, and TOML** (and XML) data with a single
canonical schema.

---

## 1. Canonical model

Every supported format is mapped onto one neutral tree model — the **Data Tree**
(`src/data_tree.py`, paper Definition 1):

| Format concept            | Data Tree representation                                  |
|---------------------------|----------------------------------------------------------|
| object / map / table      | d-node of kind `MAP`, one child d-edge per key            |
| array / sequence          | d-node of kind `SEQUENCE`, child d-edges labelled `ITEM` (`[]`) |
| scalar (string/num/bool/null) | leaf d-node of kind `SCALAR`, value + a `VDom` hint   |
| XML element               | d-edge (symbol = element name) + child d-node            |

A **Schema Automaton** (`src/schema_automaton.py`, Definition 2) is a
deterministic automaton over Data Trees:

```
A = (Q, X, q0, δ, Content, VDom)
```

* `Q`        — states (each models a data *type*)
* `X`        — symbols (element names / object keys / the array marker `[]`)
* `δ`        — transition function `Q × X → Q ∪ {⊥}`
* `Content`  — per-state **content model** describing permissible children
* `VDom`     — per-state **value domain** describing permissible scalar values

### The key generalisation: `ContentModel`

The paper describes children with a *horizontal language* (HLang): a regular
language over the **ordered** child-symbol sequence — perfect for XML, wrong for
JSON/TOML/YAML objects, which are **unordered** with unique keys.

This project abstracts the per-state child constraint into a `ContentModel`
(`src/content_model.py`) with three implementations:

| Content model   | Order      | Used for                                  |
|-----------------|------------|-------------------------------------------|
| `HLang` (SequenceModel) | ordered | XML element sequences, JSON/YAML arrays |
| `MapModel`      | unordered  | JSON objects, TOML tables, YAML mappings  |
| `ScalarModel`   | leaf       | scalar values (constraint lives in `VDom`) |

All three expose the same interface (`accepts`, `is_subset_of`, `canonical_key`,
`mandatory_symbols`, `remove_symbol`, `is_empty`, …), so **every schema
algorithm is completely independent of the data format.**

`VDom` (`src/vdom.py`) covers `STRS`, `INTS`, `DECS`, `BOOL`, `NULL`, finite
enumerations, and nullability (e.g. *string-or-null*).

---

## 2. Algorithms (paper §5)

Implemented in `src/algorithms.py`, all working against the `ContentModel`
interface:

| Function              | Algorithm | Purpose                                            |
|-----------------------|-----------|----------------------------------------------------|
| `make_useful_sa`      | Alg 1     | remove inaccessible / irrational states (Tarjan SCC)|
| `minimize_sa`         | Alg 2     | partition-refinement → unique minimal canonical SA |
| `equivalent_sa`       | Alg 3     | schema equivalence (`L(A) = L(B)`)                 |
| `subschema_sa`        | Alg 4     | subschema test (`L(A) ⊆ L(B)`) + incompatibility report |
| `extract_subschema`   | Alg 5     | trim a schema to a permitted symbol subset         |

The underlying regular-language engine (`src/nfa.py`) provides Thompson
construction, subset construction, product intersection, complement over a
shared alphabet, and Hopcroft minimization, giving exact DFA-based
equivalence / inclusion tests.

---

## 3. Format-agnostic layer

`src/formats.py`:

* `tree_from_json(text)` / `tree_from_yaml(text)` / `tree_from_toml(text)` /
  `tree_from_python(obj)` — load data into canonical Data Trees.
* `infer_schema(trees)` — infer the **canonical minimal Schema Automaton** from
  sample Data Trees:
  * MAP fields are *required* iff present in every sample, else *optional*
  * SEQUENCE item types are generalised over all elements (`item+` / `item*`)
  * SCALAR domains are generalised via `VDom.union` (incl. nullability)

Because all formats collapse to the same Data Tree, **a schema inferred from
JSON samples validates equivalent YAML or TOML data for free**, and any two
schemas can be compared for equivalence / subschema regardless of origin format.

---

## 4. Usage

```python
from src import tree_from_json, tree_from_python, infer_schema

samples = [
    '{"host": "localhost", "port": 8080, "tags": ["web"]}',
    '{"host": "example.com", "port": 443, "tags": ["prod"], "tls": true}',
]
schema = infer_schema([tree_from_json(s) for s in samples])

schema.accepts(tree_from_python({"host": "h", "port": 1, "tags": ["x"]}))   # True
schema.accepts(tree_from_python({"host": "h", "tags": ["x"]}))              # False (port required)
schema.accepts(tree_from_python({"host": "h", "port": "oops", "tags": []})) # False (port must be int)
```

See `main.py` for a full walkthrough reproducing the paper's XML examples
(SA1/SA2/SA3 equivalence, subschema, extraction) **and** the JSON/TOML inference
demo.

---

## 5. Running

```bash
python main.py            # demo: paper examples + format-agnostic inference
python -m pytest tests/   # 72 tests (paper examples + format layer)
```

YAML support needs `pyyaml`; TOML uses the stdlib `tomllib` (Python 3.11+) or
`tomli`.

---

## 6. Layout

```
src/
  nfa.py             NFA/DFA engine (Thompson, subset construction, Hopcroft)
  content_model.py   ContentModel ABC + MapModel + ScalarModel
  hlang.py           HLang — the ordered (sequence) content model
  vdom.py            value domains (STRS/INTS/DECS/BOOL/NULL/enum/nullable)
  data_tree.py       Data Tree (Definition 1)
  schema_automaton.py Schema Automaton (Definition 2) + validation (Definition 3)
  algorithms.py      Algorithms 1–5
  formats.py         JSON/YAML/TOML loaders + schema inference
tests/
  test_paper.py      reproduces the CIKM 2010 examples
  test_formats.py    map model, loaders, inference, cross-format validation
main.py              runnable demonstration
```
