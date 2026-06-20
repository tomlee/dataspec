"""Infer a Schema from one or more example Documents."""

from __future__ import annotations

import datetime as _dt
from typing import Any, List

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
    ScalarType,
    Schema,
    Type,
)


def infer(samples, open_objects: bool = False) -> Schema:
    """Build a Schema that accepts every sample (and similar documents).

    * object fields are *required* iff present in every sample, else optional;
    * arrays generalise their items and take a `{min,max}` from observed lengths;
    * scalars union their kinds (and become nullable if any sample was null).

    Set ``open_objects=True`` to infer open objects (extra keys allowed).

    Samples may be plain Python Documents or :class:`~dataspec.document.Doc`
    objects (which are unwrapped automatically).
    """
    from .document import Doc
    samples = [s.to_data() if isinstance(s, Doc) else s for s in samples]
    if not samples:
        raise SchemaError("cannot infer a schema from zero samples")
    root = _infer(samples, open_objects)
    return Schema(root)


def _kind_of(v: Any) -> str:
    # Note: bool is intentionally classified as "S" (scalar) here, even
    # though isinstance(v, bool) is also true for int checks elsewhere --
    # this function only decides object/array/scalar *structure*, and a
    # bool mixed with an object/array must hit the same mixed-shape
    # SchemaError as any other scalar (previously it didn't, and a sample
    # like [False, {}] crashed with a raw AttributeError instead).
    if isinstance(v, dict):
        return "O"
    if isinstance(v, list):
        return "A"
    return "S"  # scalar (incl None and bool)


def _infer(values: List[Any], open_objects: bool) -> Type:
    # split out nulls -> nullability
    non_null = [v for v in values if v is not None]
    nullable = len(non_null) < len(values)
    if not non_null:
        return ScalarType(set(), nullable=True)

    kinds = {_kind_of(v) for v in non_null}
    structural = kinds & {"O", "A"}
    if len(structural) > 1:
        raise SchemaError("cannot infer one type for a mix of object and array")
    if structural and "S" in kinds:
        raise SchemaError("cannot infer one type for a mix of structure and scalar "
                          "(non-null union of unlike shapes is unsupported)")
    if "O" in structural:
        return _infer_object(non_null, nullable, open_objects)
    if "A" in structural:
        return _infer_array(non_null, nullable, open_objects)
    return _infer_scalar(non_null, nullable)


def _infer_object(objs, nullable, open_objects) -> ObjectType:
    n = len(objs)
    counts, by_key = {}, {}
    for o in objs:
        for k, v in o.items():
            counts[k] = counts.get(k, 0) + 1
            by_key.setdefault(k, []).append(v)
    fields = {}
    for k, vals in by_key.items():
        fields[k] = Field(_infer(vals, open_objects), counts[k] == n)
    rest = AnyType() if open_objects else None
    return ObjectType(fields, rest, nullable=nullable)


def _infer_array(arrays, nullable, open_objects) -> ArrayType:
    items = []
    for a in arrays:
        items.extend(a)
    if not items:
        # only ever saw empty arrays — no element type observed -> empty-only
        return ArrayType(ScalarType(set(), nullable=True), 0, 0, nullable=nullable)
    # generalise permissively on length: any count is allowed (the samples never
    # show that a particular length is *required*), so don't constrain min/max
    return ArrayType(_infer(items, open_objects), 0, None, nullable=nullable)


def _infer_scalar(values, nullable) -> ScalarType:
    kinds = set()
    for v in values:
        kinds.add(_scalar_kind(v))
    if NUMBER in kinds:
        kinds.discard(INTEGER)
    return ScalarType(kinds, nullable=nullable)


def _scalar_kind(v: Any) -> str:
    if isinstance(v, bool):
        return BOOLEAN
    if isinstance(v, int):
        return INTEGER
    if isinstance(v, float):
        return NUMBER
    if isinstance(v, _dt.datetime):
        return DATETIME
    if isinstance(v, _dt.date):
        return DATE
    if isinstance(v, _dt.time):
        return TIME
    return STRING
