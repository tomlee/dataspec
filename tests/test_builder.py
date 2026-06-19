"""The schema builder: Python construction equivalent to the DSL."""
import pytest

from dataspec import (
    schema, obj, arr, mapping, ref, enum, optional, nullable,
    string, integer, number, boolean, any as any_t,
    parse_schema, doc, SchemaError,
)


class TestBuilderEquivalence:
    def test_simple_object(self):
        built = schema(obj(name=string, age=integer))
        dsl = parse_schema("root { name: string, age: integer }")
        assert built.equivalent(dsl)

    def test_optional_field(self):
        built = schema(obj(name=string, age=optional(integer)))
        dsl = parse_schema("root { name: string, age?: integer }")
        assert built.equivalent(dsl)

    def test_array(self):
        built = schema(obj(xs=arr(string)))
        dsl = parse_schema("root { xs: [string] }")
        assert built.equivalent(dsl)

    def test_array_bounds(self):
        built = schema(arr(integer, min=2, max=3))
        dsl = parse_schema("root [integer]{2,3}")
        assert built.equivalent(dsl)

    def test_nullable(self):
        built = schema(obj(v=nullable(boolean)))
        dsl = parse_schema("root { v: boolean? }")
        assert built.equivalent(dsl)

    def test_map(self):
        built = schema(mapping(integer))
        dsl = parse_schema("root { [string]: integer }")
        assert built.equivalent(dsl)

    def test_enum(self):
        built = schema(obj(status=enum("open", "shipped")))
        dsl = parse_schema('root { status: "open" | "shipped" }')
        assert built.equivalent(dsl)

    def test_scalar_union(self):
        built = schema(obj(v=ScalarUnion()))
        dsl = parse_schema("root { v: integer | string }")
        assert built.equivalent(dsl)

    def test_any(self):
        built = schema(obj(meta=any_t))
        dsl = parse_schema("root { meta: any }")
        assert built.equivalent(dsl)

    def test_named_ref_and_recursion(self):
        node = obj(value=integer, kids=arr(ref("Node")))
        built = schema(ref("Node"), Node=node)
        dsl = parse_schema("type Node = { value: integer, kids: [Node] }\nroot Node")
        assert built.equivalent(dsl)


def ScalarUnion():
    from dataspec import ScalarType, INTEGER, STRING
    return ScalarType({INTEGER, STRING})


class TestBuilderValidation:
    def test_validates_a_doc(self):
        s = schema(obj(name=string, tags=arr(string)))
        assert s.validate(doc({"name": "Ann", "tags": ["x"]})).ok
        assert not s.validate(doc({"name": 1, "tags": ["x"]})).ok

    def test_enum_rejects_outside_set(self):
        s = schema(obj(status=enum("open", "shipped")))
        assert not s.accepts(doc({"status": "closed"}))


class TestBuilderErrors:
    def test_field_must_be_a_type(self):
        with pytest.raises(SchemaError):
            obj(name="string")               # a str, not a type

    def test_arr_needs_type(self):
        with pytest.raises(SchemaError):
            arr("string")

    def test_enum_needs_values(self):
        with pytest.raises(SchemaError):
            enum()

    def test_nullable_rejects_optional(self):
        with pytest.raises(SchemaError):
            nullable(optional(string))

    def test_schema_checks_refs(self):
        with pytest.raises(SchemaError):
            schema(ref("Missing"))


class TestSchemaGetters:
    def test_field_and_children(self):
        s = schema(obj(name=string, age=optional(integer)))
        assert s.root.field("name") is string
        assert set(n for n, _ in s.root.children()) == {"name", "age"}

    def test_field_missing_raises(self):
        with pytest.raises(SchemaError):
            obj(name=string).field("nope")

    def test_array_children(self):
        a = arr(string)
        assert a.children() == [("[]", string)]

    def test_map_children_include_rest(self):
        m = mapping(integer)
        assert ("[rest]", integer) in m.children()
