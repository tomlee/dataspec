"""Demo 8 — The Data Tree as a format-neutral hub.

Parse one serialization syntax into the canonical Data Tree, emit another.
JSON / YAML / TOML are codecs around one model; transcoding is just
load-then-emit.
"""
from _bootstrap import header
from src import (
    tree_from_json, tree_from_toml, tree_from_python,
    tree_to_python, to_json, to_yaml, to_toml, SerializationError,
)

JSON = '{"name": "Ann", "age": 30, "active": true, "scores": [9.5, 8.0], ' \
       '"address": {"city": "HK", "zip": "999"}}'


def main() -> None:
    header("JSON string  ->  Data Tree  ->  TOML string")
    tree = tree_from_json(JSON)
    print(to_toml(tree))

    header("...the same Data Tree  ->  YAML")
    print(to_yaml(tree))

    header("Type fidelity is preserved via per-node type hints")
    print('age 30 stays an integer; zip "999" stays a string:')
    print("  ", to_json(tree_from_python({"age": 30, "zip": "999"})))

    header("Round-trip is lossless for the JSON data model")
    import json
    print("json -> tree -> python == original:",
          tree_to_python(tree) == json.loads(JSON))

    header("TOML is a partial projection — limits are surfaced clearly")
    for label, doc in [("null value", {"x": None}),
                       ("top-level array", [1, 2, 3])]:
        try:
            to_toml(tree_from_python(doc))
        except SerializationError as exc:
            print(f"  {label}: {exc}")

    header("YAML / JSON have no such limits")
    print("  null in YAML:", repr(to_yaml(tree_from_python({"x": None})).strip()))
    print("  top-level array in JSON:", to_json(tree_from_python([1, 2, 3])))

    header("TOML  ->  Data Tree  ->  JSON")
    toml_doc = 'title = "demo"\n[owner]\nname = "Tom"\nnums = [1, 2, 3]\n'
    print(to_json(tree_from_toml(toml_doc), indent=2))


if __name__ == "__main__":
    main()
