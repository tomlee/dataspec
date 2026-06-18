"""
Tests for Data Tree serialization — the canonical model as a format hub:
parse one syntax into a Data Tree, emit another.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import json
import pytest

from src import (
    tree_from_python, tree_from_json, tree_from_toml,
    tree_to_python, to_json, to_yaml, to_toml, SerializationError,
)

yaml = pytest.importorskip("yaml")
tomllib = pytest.importorskip("tomllib")


SAMPLE = {
    "name": "Ann",
    "age": 30,
    "active": True,
    "ratio": 0.5,
    "tags": ["x", "y"],
    "zip": "999",                 # a string that looks numeric
    "address": {"city": "HK", "nums": [1, 2, 3]},
}


# ===========================================================================
# tree_to_python — the hub (inverse of tree_from_python)
# ===========================================================================

class TestHub:
    def test_round_trip_python(self):
        assert tree_to_python(tree_from_python(SAMPLE)) == SAMPLE

    def test_type_fidelity(self):
        obj = tree_to_python(tree_from_python({"i": 1, "f": 1.0, "b": True, "s": "1"}))
        assert obj["i"] == 1 and isinstance(obj["i"], int)
        assert obj["f"] == 1.0 and isinstance(obj["f"], float)
        assert obj["b"] is True
        assert obj["s"] == "1" and isinstance(obj["s"], str)   # not coerced to int

    def test_null_round_trips(self):
        assert tree_to_python(tree_from_python({"x": None})) == {"x": None}

    def test_top_level_scalar_and_array(self):
        assert tree_to_python(tree_from_python(42)) == 42
        assert tree_to_python(tree_from_python([1, "a", True])) == [1, "a", True]

    def test_nested(self):
        deep = {"a": {"b": {"c": [1, {"d": 2}]}}}
        assert tree_to_python(tree_from_python(deep)) == deep


# ===========================================================================
# JSON / YAML emit and round-trip
# ===========================================================================

class TestJsonYaml:
    def test_json_round_trip(self):
        text = json.dumps(SAMPLE)
        assert json.loads(to_json(tree_from_json(text))) == SAMPLE

    def test_json_pretty(self):
        out = to_json(tree_from_python({"a": 1}), indent=2)
        assert "\n" in out and json.loads(out) == {"a": 1}

    def test_yaml_round_trip(self):
        out = to_yaml(tree_from_python(SAMPLE))
        assert yaml.safe_load(out) == SAMPLE

    def test_yaml_handles_null(self):
        out = to_yaml(tree_from_python({"x": None}))
        assert yaml.safe_load(out) == {"x": None}


# ===========================================================================
# TOML emit and its (documented) limitations
# ===========================================================================

class TestToml:
    def test_toml_round_trip(self):
        out = to_toml(tree_from_python(SAMPLE))
        assert tomllib.loads(out) == SAMPLE

    def test_json_to_toml_to_json(self):
        text = json.dumps(SAMPLE)
        toml_text = to_toml(tree_from_json(text))
        back = tree_to_python(tree_from_toml(toml_text))
        assert back == SAMPLE

    def test_toml_rejects_null(self):
        with pytest.raises(SerializationError):
            to_toml(tree_from_python({"x": None}))

    def test_toml_rejects_nested_null(self):
        with pytest.raises(SerializationError):
            to_toml(tree_from_python({"a": {"b": None}}))

    def test_toml_rejects_top_level_array(self):
        with pytest.raises(SerializationError):
            to_toml(tree_from_python([1, 2, 3]))

    def test_toml_rejects_top_level_scalar(self):
        with pytest.raises(SerializationError):
            to_toml(tree_from_python("hello"))


# ===========================================================================
# Cross-format transcoding (the headline use case)
# ===========================================================================

class TestCrossFormat:
    def test_json_string_to_toml_string(self):
        toml_text = to_toml(tree_from_json('{"name": "Ann", "tags": ["a", "b"]}'))
        assert tomllib.loads(toml_text) == {"name": "Ann", "tags": ["a", "b"]}

    def test_toml_string_to_json_string(self):
        json_text = to_json(tree_from_toml('title = "t"\n[o]\nk = 1\n'))
        assert json.loads(json_text) == {"title": "t", "o": {"k": 1}}

    def test_json_to_yaml_to_json_preserves_data(self):
        original = '{"a": 1, "b": [true, null, "s"], "c": {"d": 2.5}}'
        yaml_text = to_yaml(tree_from_json(original))
        back = tree_to_python(tree_from_python(yaml.safe_load(yaml_text)))
        assert back == json.loads(original)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
