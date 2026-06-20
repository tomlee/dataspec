"""A programmatic builder for schemas — Python expressions instead of DSL text.

Three doors lead to the same schema object tree: :func:`~dataspec.parse_schema`
(text), :func:`~dataspec.infer` (examples), and this builder (code).  The builder
is handy when schemas are generated or composed, where a string DSL is awkward::

    from dataspec import obj, arr, optional, schema, t

    s = schema(obj(
        name = t.string,
        age  = optional(t.integer),
        tags = arr(t.string),
    ))
    s.validate(doc({"name": "Ann", "tags": ["x"]}))

It produces ordinary :class:`~dataspec.schema.ObjectType` / ``ScalarType`` / …
values — nothing new to learn on the read side.
"""

from __future__ import annotations

import datetime as _dt
from typing import Any
from typing import Optional as _Opt

from .errors import SchemaError
from .schema import (
    BOOLEAN,
    DATE,
    DATETIME,
    INTEGER,
    NUMBER,
    STRING,
    TIME,
    AnyType,
    ArrayType,
    Field,
    ObjectType,
    RefType,
    ScalarType,
    Schema,
    Type,
)


# -- type atoms, namespaced under `t` to avoid shadowing builtins/stdlib --
class _Types:
    """The schema type atoms, e.g. ``t.string``, ``t.date``, ``t.any``.

    Namespaced (rather than bare top-level names) so they never shadow Python's
    ``any`` or the stdlib ``datetime`` / ``date`` / ``time`` modules.  Treat the
    atoms as immutable — ``nullable()`` returns a fresh copy.
    """
    string = ScalarType({STRING})
    integer = ScalarType({INTEGER})
    number = ScalarType({NUMBER})
    boolean = ScalarType({BOOLEAN})
    date = ScalarType({DATE})
    time = ScalarType({TIME})
    datetime = ScalarType({DATETIME})
    any = AnyType()

    def __repr__(self) -> str:
        return ("dataspec.t — type atoms: string, integer, number, boolean, "
                "date, time, datetime, any")


t = _Types()


class _Optional:
    """Marker wrapping a field type to mark it not-required (see :func:`optional`)."""
    __slots__ = ("type",)

    def __init__(self, type: Type) -> None:
        self.type = type


def optional(t: Type) -> _Optional:
    """Mark an object field as optional (used as a value inside :func:`obj`)."""
    return _Optional(t)


def nullable(t: Type) -> Type:
    """Return a copy of a type that also accepts ``null``."""
    if isinstance(t, _Optional):
        raise SchemaError("nullable() takes a type, not optional(...)")
    if isinstance(t, AnyType):
        return t                                  # any already includes null
    if isinstance(t, ScalarType):
        return ScalarType(t.kinds, nullable=True, enum=t.enum)
    if isinstance(t, ArrayType):
        return ArrayType(t.item, t.min, t.max, nullable=True)
    if isinstance(t, ObjectType):
        return ObjectType(t.fields, t.rest, nullable=True)
    if isinstance(t, RefType):
        return RefType(t.name, nullable=True)
    raise SchemaError(f"cannot make {t!r} nullable")


def obj(**fields: Any) -> ObjectType:
    """A closed object type.  Each value is a type, or ``optional(type)``."""
    built = {}
    for name, spec in fields.items():
        if isinstance(spec, _Optional):
            built[name] = Field(spec.type, required=False)
        elif isinstance(spec, Type):
            built[name] = Field(spec, required=True)
        else:
            raise SchemaError(
                f"field {name!r} must be a type or optional(type), got {spec!r}")
    return ObjectType(built)


def mapping(value_type: Type) -> ObjectType:
    """A map ``{[string]: T}`` — any string keys, all values of ``value_type``."""
    if not isinstance(value_type, Type):
        raise SchemaError(f"mapping() needs a type, got {value_type!r}")
    return ObjectType({}, rest=value_type)


def arr(item: Type, min: int = 0, max: _Opt[int] = None) -> ArrayType:
    """An array of ``item``, with an optional length bound."""
    if not isinstance(item, Type):
        raise SchemaError(f"arr() needs an item type, got {item!r}")
    return ArrayType(item, min, max)


def ref(name: str) -> RefType:
    """A reference to a named type (for reuse / recursion)."""
    return RefType(name)


def enum(*values: Any) -> ScalarType:
    """A scalar restricted to a fixed set of literal values."""
    if not values:
        raise SchemaError("enum() needs at least one value")
    for v in values:
        if not isinstance(v, (bool, int, float, str, _dt.date, _dt.time)):
            raise SchemaError(f"enum value {v!r} is not a scalar literal")
    # `kinds` stays empty: it must never be auto-derived from the literals'
    # own types, or `_check_scalar`'s kind-fallback would accept any value
    # of that kind, not just the specific literals (e.g. enum("a", "b")
    # would wrongly accept any string). To allow a *kind* alongside an enum
    # (`integer | "foo"`-equivalent), construct ScalarType(kinds, enum=...)
    # directly -- enum() itself is pure-enum-only, like the DSL's `"a"|"b"`.
    return ScalarType(set(), enum=set(values))


def schema(root: Type, **types: Type) -> Schema:
    """Assemble a :class:`Schema` from a root type and optional named types."""
    s = Schema(root, dict(types) if types else None)
    s.check_refs()
    return s
