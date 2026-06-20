"""infer, equivalent, compatible_with, normalize."""
import pytest

from dataspec import Doc, SchemaError, doc, infer, parse_schema, read_json


# ------------------------------------------------------------- infer
class TestInfer:
    def test_accepts_all_samples(self):
        samples = [
            {"name": "Ann", "age": 30},
            {"name": "Bob", "age": 25},
        ]
        s = infer(samples)
        for sample in samples:
            assert s.validate(doc(sample)).ok

    def test_optional_field(self):
        s = infer([{"name": "Ann", "age": 30}, {"name": "Bob"}])
        assert s.validate(doc({"name": "Cy"})).ok          # age optional
        assert not s.validate(doc({"age": 1})).ok          # name required

    def test_scalar_union_is_sound(self):
        # the classic soundness check: schema must accept its own samples
        samples = [{"v": 1}, {"v": "x"}]
        s = infer(samples)
        for sample in samples:
            assert s.validate(doc(sample)).ok

    def test_int_float_widens_to_number(self):
        s = infer([{"v": 1}, {"v": 2.5}])
        assert s.validate(doc({"v": 7})).ok
        assert s.validate(doc({"v": 7.7})).ok

    def test_nullable(self):
        s = infer([{"v": "a"}, {"v": None}])
        assert s.validate(doc({"v": "b"})).ok
        assert s.validate(doc({"v": None})).ok
        assert not s.validate(doc({"v": 1})).ok

    def test_array_generalises_on_length(self):
        # inference is permissive on length: any count of the inferred item type
        s = infer([{"xs": [1, 2]}, {"xs": [1, 2, 3, 4]}])
        assert s.validate(doc({"xs": [1, 2, 3]})).ok
        assert s.validate(doc({"xs": [9]})).ok
        assert s.validate(doc({"xs": []})).ok               # empty allowed too
        assert not s.validate(doc({"xs": ["nope"]})).ok     # but item type is enforced

    def test_only_empty_arrays_infer_empty_only(self):
        s = infer([{"xs": []}])
        assert s.validate(doc({"xs": []})).ok
        assert not s.validate(doc({"xs": [1]})).ok          # no element type was seen

    def test_mixed_structure_raises(self):
        with pytest.raises(SchemaError):
            infer([{"v": 1}, {"v": {"x": 1}}])

    def test_mixed_object_and_array_raises(self):
        with pytest.raises(SchemaError):
            infer([{"v": [1]}, {"v": {"x": 1}}])

    def test_bool_mixed_with_object_raises_cleanly(self):
        # found by property-based fuzzing: a bool was classified separately
        # from other scalars in the structural-mixing check, so this used to
        # crash with a raw AttributeError ('bool' object has no attribute
        # 'items') instead of the same clean SchemaError plain scalars get.
        with pytest.raises(SchemaError):
            infer([{"v": False}, {"v": {}}])

    def test_bool_mixed_with_array_raises_cleanly(self):
        with pytest.raises(SchemaError):
            infer([{"v": False}, {"v": []}])

    def test_bool_samples_still_infer_normally(self):
        # the fix above must not change ordinary boolean inference
        s = infer([{"v": True}, {"v": False}])
        assert s.validate(doc({"v": True})).ok
        assert s.validate(doc({"v": False})).ok
        assert not s.validate(doc({"v": 1})).ok

    def test_round_trip_through_json(self):
        s = infer([read_json('{"id": 1, "tags": ["a"]}')])
        assert s.validate(Doc.from_json('{"id": 9, "tags": ["b", "c"]}')).ok


# ------------------------------------------------------ equivalent / compatible
class TestComparison:
    def test_equivalent_self(self):
        s = parse_schema("root { a: integer, b: string }")
        assert s.equivalent(s)

    def test_equivalent_reordered_fields(self):
        a = parse_schema("root { a: integer, b: string }")
        b = parse_schema("root { b: string, a: integer }")
        assert a.equivalent(b)

    def test_not_equivalent(self):
        a = parse_schema("root { a: integer }")
        b = parse_schema("root { a: string }")
        assert not a.equivalent(b)

    def test_compatible_optional_relaxation(self):
        # making a field optional is backward compatible
        strict = parse_schema("root { a: integer, b: integer }")
        loose = parse_schema("root { a: integer, b?: integer }")
        assert strict.compatible_with(loose)
        assert not loose.compatible_with(strict)

    def test_compatible_added_optional_field(self):
        v1 = parse_schema("root { a: integer }")
        v2 = parse_schema("root { a: integer, b?: integer }")
        assert v1.compatible_with(v2)        # every v1 doc is valid under v2

    def test_compatible_widened_scalar(self):
        narrow = parse_schema("root { v: integer }")
        wide = parse_schema("root { v: integer | string }")
        assert narrow.compatible_with(wide)
        assert not wide.compatible_with(narrow)

    def test_compatible_array_bounds(self):
        a = parse_schema("root [integer]{2,3}")
        b = parse_schema("root [integer]{1,5}")
        assert a.compatible_with(b)
        assert not b.compatible_with(a)

    def test_compatible_map_value_widening(self):
        narrow = parse_schema("root { [string]: integer }")
        wide = parse_schema("root { [string]: number }")
        assert narrow.compatible_with(wide)
        assert not wide.compatible_with(narrow)

    def test_anything_is_compatible_with_any(self):
        concrete = parse_schema("root { a: integer }")
        anything = parse_schema("root any")
        assert concrete.compatible_with(anything)
        assert not anything.compatible_with(concrete)


# ----------------------------------------------------------- normalize
class TestNormalize:
    def test_merges_identical_named_types(self):
        s = parse_schema("""
            type A = { x: integer }
            type B = { x: integer }
            root { a: A, b: B }
        """)
        n = s.normalize()
        assert len(n.types) == 1
        assert s.equivalent(n)

    def test_normalize_preserves_language(self):
        s = parse_schema("type P = { x: number, y: number }\nroot { p: P, q: P }")
        assert s.equivalent(s.normalize())
