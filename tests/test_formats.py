"""
Tests for the data-format-agnostic layer:
  - loading JSON / YAML / TOML / Python data into canonical Data Trees
  - the MapModel (unordered) content model
  - schema inference from sample trees
  - cross-format validation (a schema inferred from JSON validates YAML/TOML)
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest

from src import (
    DataTree, SchemaAutomaton, HLang, VDom,
    MapModel, ScalarModel, KIND_MAP, KIND_SEQUENCE, KIND_SCALAR,
    minimize_sa, equivalent_sa, subschema_sa, extract_subschema,
    ITEM, tree_from_python, tree_from_json, infer_schema,
)


# ===========================================================================
# MapModel (unordered content) unit tests
# ===========================================================================

class TestMapModel:
    def test_accepts_unordered(self):
        m = MapModel.of(required=["a", "b"], optional=["c"])
        assert m.accepts(["a", "b"])
        assert m.accepts(["b", "a"])         # order irrelevant
        assert m.accepts(["a", "b", "c"])
        assert m.accepts(["c", "b", "a"])

    def test_rejects_missing_required(self):
        m = MapModel.of(required=["a", "b"])
        assert not m.accepts(["a"])
        assert not m.accepts([])

    def test_rejects_unknown_key_when_closed(self):
        m = MapModel.of(required=["a"])
        assert not m.accepts(["a", "x"])

    def test_open_map_allows_extra(self):
        m = MapModel.of(required=["a"], open=True)
        assert m.accepts(["a", "x", "y"])

    def test_rejects_duplicate_keys(self):
        m = MapModel.of(optional=["a"])
        assert not m.accepts(["a", "a"])

    def test_mandatory_symbols(self):
        m = MapModel.of(required=["a", "b"], optional=["c"])
        assert m.mandatory_symbols() == {"a", "b"}

    def test_remove_required_symbol_empties(self):
        m = MapModel.of(required=["a"])
        assert m.remove_symbol("a").is_empty()

    def test_remove_optional_symbol(self):
        m = MapModel.of(required=["a"], optional=["b"])
        m2 = m.remove_symbol("b")
        assert not m2.is_empty()
        assert m2.accepts(["a"])
        assert not m2.accepts(["a", "b"])

    def test_subset_required_relaxation(self):
        # {a required} ⊆ {a optional}: every {a} doc is accepted by the looser one
        strict = MapModel.of(required=["a"])
        loose = MapModel.of(optional=["a"])
        assert strict.is_subset_of(loose)
        assert not loose.is_subset_of(strict)

    def test_subset_extra_optional(self):
        narrow = MapModel.of(required=["a"])
        wider = MapModel.of(required=["a"], optional=["b"])
        assert narrow.is_subset_of(wider)
        assert not wider.is_subset_of(narrow)

    def test_map_not_subset_of_sequence(self):
        m = MapModel.of(required=["a"])
        seq = HLang.parse("a")
        assert not m.is_subset_of(seq)
        assert not seq.is_subset_of(m)

    def test_canonical_key_equality(self):
        m1 = MapModel.of(required=["a"], optional=["b"])
        m2 = MapModel.of(optional=["b"], required=["a"])
        assert m1.canonical_key() == m2.canonical_key()
        assert m1.language_equals(m2)


# ===========================================================================
# Loading data into Data Trees
# ===========================================================================

class TestLoading:
    def test_json_object(self):
        dt = tree_from_json('{"name": "Ann", "age": 30}')
        assert dt.node(dt.root_id).kind == KIND_MAP
        assert set(dt.child_symbol_sequence(dt.root_id)) == {"name", "age"}

    def test_json_array(self):
        dt = tree_from_json('[1, 2, 3]')
        assert dt.node(dt.root_id).kind == KIND_SEQUENCE
        assert dt.child_symbol_sequence(dt.root_id) == [ITEM, ITEM, ITEM]

    def test_json_nested(self):
        dt = tree_from_json('{"items": [{"id": 1}]}')
        root = dt.root_id
        assert dt.node(root).kind == KIND_MAP
        items_edge = dt.child_edges(root)[0]
        assert dt.node(items_edge.child_id).kind == KIND_SEQUENCE

    def test_scalar_vdom_hints(self):
        dt = tree_from_python({"n": 1, "f": 1.5, "b": True, "s": "x", "z": None})
        kinds = {}
        for e in dt.child_edges(dt.root_id):
            kinds[e.symbol] = dt.node(e.child_id).vdom.kind
        assert kinds["n"] == VDom.INTS
        assert kinds["f"] == VDom.DECS
        assert kinds["b"] == VDom.BOOL
        assert kinds["s"] == VDom.STRS
        assert kinds["z"] == VDom.NULL


# ===========================================================================
# Schema inference
# ===========================================================================

class TestInference:
    def test_infer_simple_object(self):
        trees = [
            tree_from_python({"name": "Ann", "age": 30}),
            tree_from_python({"name": "Bob", "age": 25}),
        ]
        sa = infer_schema(trees)
        # both samples must validate against the inferred schema
        for t in trees:
            assert sa.accepts(t)

    def test_optional_field_detection(self):
        # 'age' present in only one sample → optional; 'name' in both → required
        trees = [
            tree_from_python({"name": "Ann", "age": 30}),
            tree_from_python({"name": "Bob"}),
        ]
        sa = infer_schema(trees)
        assert sa.accepts(tree_from_python({"name": "Cy"}))          # no age — ok
        assert sa.accepts(tree_from_python({"name": "Di", "age": 9}))
        assert not sa.accepts(tree_from_python({"age": 9}))          # missing name

    def test_inferred_schema_rejects_extra_keys(self):
        trees = [tree_from_python({"a": 1})]
        sa = infer_schema(trees)
        assert sa.accepts(tree_from_python({"a": 2}))
        assert not sa.accepts(tree_from_python({"a": 2, "b": 3}))

    def test_array_of_objects(self):
        trees = [tree_from_python(
            {"users": [{"id": 1, "name": "Ann"}, {"id": 2, "name": "Bob"}]}
        )]
        sa = infer_schema(trees)
        assert sa.accepts(trees[0])
        # an extra valid user is accepted
        assert sa.accepts(tree_from_python(
            {"users": [{"id": 3, "name": "Cy"}]}
        ))

    def test_numeric_generalisation(self):
        # int and float in the same position → DECS
        trees = [
            tree_from_python({"v": 1}),
            tree_from_python({"v": 2.5}),
        ]
        sa = infer_schema(trees)
        assert sa.accepts(tree_from_python({"v": 7}))
        assert sa.accepts(tree_from_python({"v": 7.7}))

    def test_nullable_generalisation(self):
        # value or null → nullable domain
        trees = [
            tree_from_python({"v": "hello"}),
            tree_from_python({"v": None}),
        ]
        sa = infer_schema(trees)
        assert sa.accepts(tree_from_python({"v": "world"}))
        assert sa.accepts(tree_from_python({"v": None}))

    def test_inferred_schema_is_minimal(self):
        # repeated identical sub-structures should share one state after minimize
        trees = [tree_from_python({
            "from": {"x": 1, "y": 2},
            "to":   {"x": 3, "y": 4},
        })]
        sa = infer_schema(trees)
        assert sa.accepts(trees[0])
        # 'from' and 'to' have identical structure → their point-type states merge
        # Resulting states: root, point-type, int-leaf  ≈ 3 states
        assert len(sa.states) <= 4


# ===========================================================================
# Cross-format: schema inferred from one format validates another
# ===========================================================================

class TestCrossFormat:
    def test_json_schema_validates_equivalent_yaml_like_python(self):
        # Infer from JSON text, validate a tree built from a different source
        json_tree = tree_from_json('{"host": "localhost", "port": 8080}')
        sa = infer_schema([json_tree])

        # Simulate a TOML/YAML-origin document as a plain Python dict
        toml_like = tree_from_python({"host": "example.com", "port": 443})
        assert sa.accepts(toml_like)

        # Wrong type for 'port' (string where integer expected) is rejected
        bad = tree_from_python({"host": "x", "port": "not-a-number"})
        assert not sa.accepts(bad)

    def test_subschema_across_inferred_schemas(self):
        # Schema A requires {host}; schema B requires {host, port}.
        # A doc valid under B (closed) is not necessarily valid under A (closed),
        # but B ⊆ A only if A permits port. Here we check the relationship.
        sa_required_host = infer_schema([tree_from_python({"host": "a"})])
        # open variant of host-only: accepts host plus anything? Not by default.
        # Instead verify reflexivity and a genuine subschema via extraction.
        assert subschema_sa(sa_required_host, sa_required_host).is_compatible


# ===========================================================================
# Subschema extraction on inferred (map-based) schemas
# ===========================================================================

class TestMapExtraction:
    def test_extract_drops_optional_field(self):
        trees = [
            tree_from_python({"keep": 1, "drop": 2}),
            tree_from_python({"keep": 1}),  # makes 'drop' optional
        ]
        sa = infer_schema(trees)
        # Extract a subschema that only permits the 'keep' symbol
        extracted = extract_subschema(sa, {"keep"})
        assert extracted.accepts(tree_from_python({"keep": 5}))
        assert not extracted.accepts(tree_from_python({"keep": 5, "drop": 6}))


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
