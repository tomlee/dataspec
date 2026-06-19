"""The schema builder: Python construction equivalent to the DSL."""
import pytest

from dataspec import (
    INTEGER,
    STRING,
    ScalarType,
    SchemaError,
    arr,
    doc,
    enum,
    mapping,
    nullable,
    obj,
    optional,
    parse_schema,
    ref,
    schema,
    t,
)


class TestBuilderEquivalence:
    def test_simple_object(self):
        built = schema(obj(name=t.string, age=t.integer))
        dsl = parse_schema("root { name: string, age: integer }")
        assert built.equivalent(dsl)

    def test_optional_field(self):
        built = schema(obj(name=t.string, age=optional(t.integer)))
        dsl = parse_schema("root { name: string, age?: integer }")
        assert built.equivalent(dsl)

    def test_array(self):
        built = schema(obj(xs=arr(t.string)))
        dsl = parse_schema("root { xs: [string] }")
        assert built.equivalent(dsl)

    def test_array_bounds(self):
        built = schema(arr(t.integer, min=2, max=3))
        dsl = parse_schema("root [integer]{2,3}")
        assert built.equivalent(dsl)

    def test_nullable(self):
        built = schema(obj(v=nullable(t.boolean)))
        dsl = parse_schema("root { v: boolean? }")
        assert built.equivalent(dsl)

    def test_map(self):
        built = schema(mapping(t.integer))
        dsl = parse_schema("root { [string]: integer }")
        assert built.equivalent(dsl)

    def test_enum(self):
        built = schema(obj(status=enum("open", "shipped")))
        dsl = parse_schema('root { status: "open" | "shipped" }')
        assert built.equivalent(dsl)

    def test_scalar_union(self):
        built = schema(obj(v=ScalarType({INTEGER, STRING})))
        dsl = parse_schema("root { v: integer | string }")
        assert built.equivalent(dsl)

    def test_any(self):
        built = schema(obj(meta=t.any))
        dsl = parse_schema("root { meta: any }")
        assert built.equivalent(dsl)

    def test_named_ref_and_recursion(self):
        node = obj(value=t.integer, kids=arr(ref("Node")))
        built = schema(ref("Node"), Node=node)
        dsl = parse_schema("type Node = { value: integer, kids: [Node] }\nroot Node")
        assert built.equivalent(dsl)


class TestBuilderValidation:
    def test_validates_a_doc(self):
        s = schema(obj(name=t.string, tags=arr(t.string)))
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
            nullable(optional(t.string))

    def test_schema_checks_refs(self):
        with pytest.raises(SchemaError):
            schema(ref("Missing"))


class TestSchemaGetters:
    def test_field_and_children(self):
        s = schema(obj(name=t.string, age=optional(t.integer)))
        assert s.root.field("name") is t.string
        assert set(n for n, _ in s.root.children()) == {"name", "age"}

    def test_field_missing_raises(self):
        with pytest.raises(SchemaError):
            obj(name=t.string).field("nope")

    def test_array_children(self):
        a = arr(t.string)
        assert a.children() == [("[]", t.string)]

    def test_map_children_include_rest(self):
        m = mapping(t.integer)
        assert ("[rest]", t.integer) in m.children()
