"""infer, equivalent, compatible_with, normalize."""
import datetime

import pytest

from dataspec import (
    Doc,
    SchemaError,
    doc,
    enum,
    infer,
    mapping,
    obj,
    parse_schema,
    read_json,
    read_toml,
    read_xml,
    read_yaml,
    schema,
    t,
)


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


# ----------------------------- compatible_with: open-map / `rest` soundness
class TestRestCompatibility:
    """A `rest` (open-map) field can emit ANY key not explicitly named --
    including, by coincidence, one of the other schema's explicitly named
    fields. compatible_with() used to only ever compare rest-to-rest and
    named-to-named, never wildcard-to-named, so it judged a clearly-unsound
    pair "compatible". Built two ways (DSL and the Python builder) to pin
    the fix at both entry points."""

    def test_pure_map_vs_named_field_is_not_compatible_dsl(self):
        a = parse_schema("root { [string]: string }")
        b = parse_schema('root { extra?: integer, [string]: string }')
        assert not a.compatible_with(b)
        # concrete witness: a accepts it, b rejects it
        bad = doc({"extra": "hello"})
        assert a.accepts(bad)
        assert not b.accepts(bad)

    def test_pure_map_vs_named_field_is_not_compatible_builder(self):
        # obj() builds a closed record; a named field plus a map rest (what
        # the DSL form `{ extra?: integer, [string]: string }` means) needs
        # ObjectType directly, since obj() alone has no `rest=` parameter.
        from dataspec.schema import Field, ObjectType

        a = schema(mapping(t.string))
        b = schema(ObjectType({"extra": Field(t.integer, False)}, rest=t.string))
        assert not a.compatible_with(b)
        bad = doc({"extra": "hello"})
        assert a.accepts(bad)
        assert not b.accepts(bad)

    def test_map_vs_named_field_with_compatible_type_is_fine(self):
        # if the colliding field's type is widened enough to accept
        # whatever the map could emit there, it IS compatible
        a = parse_schema("root { [string]: integer }")
        b = parse_schema("root { extra?: integer | string, [string]: integer }")
        assert a.compatible_with(b)

    def test_closed_object_is_never_compatible_with_a_stricter_open_map(self):
        # sanity check the fix didn't break the already-correct closed-a case
        a = parse_schema("root { a: integer }")
        b = parse_schema("root { a: integer, [string]: integer }")
        assert a.compatible_with(b)        # closed a has nothing extra to emit
        assert not b.compatible_with(a)     # b's rest could emit keys a forbids


# ------------------------- compatible_with: temporal values inside an enum
class TestTemporalEnumCompatibility:
    """`_value_kind()` used to classify any non-bool/int/float enum literal
    as STRING, so an enum of date/time/datetime values was wrongly judged
    incompatible with a schema that accepts that kind outright."""

    def test_date_enum_compatible_with_date_kind(self):
        narrow = schema(enum(datetime.date(2024, 1, 1), datetime.date(2024, 6, 1)))
        wide = schema(t.date)
        assert narrow.compatible_with(wide)
        assert not wide.compatible_with(narrow)

    def test_datetime_enum_compatible_with_datetime_kind(self):
        narrow = schema(enum(datetime.datetime(2024, 1, 1, 12, 0)))
        wide = schema(t.datetime)
        assert narrow.compatible_with(wide)

    def test_time_enum_compatible_with_time_kind(self):
        narrow = schema(enum(datetime.time(9, 30)))
        wide = schema(t.time)
        assert narrow.compatible_with(wide)

    def test_mixed_kind_and_temporal_enum_via_dsl_and_builder_agree(self):
        # the DSL has no date-literal syntax, so this is builder-only, but
        # it should validate the same sample data the same way regardless
        # of how the schema was constructed.
        s = schema(enum(datetime.date(2024, 1, 1)))
        assert s.validate(doc(datetime.date(2024, 1, 1))).ok
        assert not s.validate(doc(datetime.date(2024, 1, 2))).ok


# --------------- DSL-built and builder-built schemas agree across formats
class TestSchemaAcrossFormats:
    """The same schema, built two different ways (DSL text and the Python
    builder), should accept the same Documents -- including ones converted
    from every supported format. XML is single-rooted, so the Document is
    wrapped under one top-level key ("order") to have a valid XML shape at
    all (see docs/formats/xml.md)."""

    DSL = '''
        type Address = { street: string, city: string }
        root {
            order: {
                id:      string,
                status:  "pending" | "shipped" | "cancelled",
                total:   number,
                address: Address,
                tags:    { [string]: string },
            },
        }
    '''

    @staticmethod
    def builder_schema():
        address_t = obj(street=t.string, city=t.string)
        order_t = obj(
            id=t.string,
            status=enum("pending", "shipped", "cancelled"),
            total=t.number,
            address=address_t,
            tags=mapping(t.string),
        )
        return schema(obj(order=order_t))

    SAMPLE = {
        "order": {
            "id": "A1",
            "status": "shipped",
            "total": 9.99,
            "address": {"street": "1 Main St", "city": "London"},
            "tags": {"region": "EU", "priority": "high"},
        }
    }

    def test_dsl_and_builder_schemas_are_equivalent(self):
        dsl_schema = parse_schema(self.DSL)
        assert dsl_schema.equivalent(self.builder_schema())

    def test_both_schemas_accept_the_plain_document(self):
        for s in (parse_schema(self.DSL), self.builder_schema()):
            assert s.validate(doc(self.SAMPLE)).ok

    def test_both_schemas_accept_json(self):
        d = read_json(
            '{"order": {"id": "A1", "status": "shipped", "total": 9.99, '
            '"address": {"street": "1 Main St", "city": "London"}, '
            '"tags": {"region": "EU", "priority": "high"}}}')
        for s in (parse_schema(self.DSL), self.builder_schema()):
            assert s.validate(doc(d)).ok

    def test_both_schemas_accept_yaml(self):
        yaml_text = """
        order:
          id: A1
          status: shipped
          total: 9.99
          address:
            street: 1 Main St
            city: London
          tags:
            region: EU
            priority: high
        """
        d = read_yaml(yaml_text)
        for s in (parse_schema(self.DSL), self.builder_schema()):
            assert s.validate(doc(d)).ok

    def test_both_schemas_accept_toml(self):
        toml_text = """
        [order]
        id = "A1"
        status = "shipped"
        total = 9.99

        [order.address]
        street = "1 Main St"
        city = "London"

        [order.tags]
        region = "EU"
        priority = "high"
        """
        d = read_toml(toml_text)
        for s in (parse_schema(self.DSL), self.builder_schema()):
            assert s.validate(doc(d)).ok

    def test_both_schemas_accept_xml(self):
        # single-rooted: the document element's tag ("order") is the one
        # top-level key, matching the schema's `order: {...}` field.
        xml_text = (
            "<order>"
            "<id>A1</id><status>shipped</status><total>9.99</total>"
            "<address><street>1 Main St</street><city>London</city></address>"
            "<tags><region>EU</region><priority>high</priority></tags>"
            "</order>"
        )
        d = read_xml(xml_text)
        for s in (parse_schema(self.DSL), self.builder_schema()):
            assert s.validate(doc(d)).ok

    def test_both_schemas_reject_an_invalid_status_regardless_of_format(self):
        bad = read_json(
            '{"order": {"id": "A1", "status": "lost", "total": 9.99, '
            '"address": {"street": "x", "city": "y"}, "tags": {}}}')
        for s in (parse_schema(self.DSL), self.builder_schema()):
            assert not s.validate(doc(bad)).ok


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
