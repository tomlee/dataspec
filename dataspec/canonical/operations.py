"""Schema operations on the canonical model.

* ``compatible_with(a, b)`` — every document ``a`` accepts is also accepted by
  ``b`` (``a`` is a subschema / ``b`` is backward-compatible).
* ``equivalent(a, b)`` — both accept exactly the same documents.
* ``normalize(s)`` — merge structurally-identical named records.

All checks are structural and order-free, and handle recursion by assuming
compatibility when a cycle repeats.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Set, Tuple

from .schema import Field, Record, Ref, Scalar, Schema

# ---------------------------------------------------------------------------
# compatible_with  /  equivalent
# ---------------------------------------------------------------------------

def compatible_with(a: Schema, b: Schema) -> bool:
    return _sub(a, a.root, b, b.root, set())


def equivalent(a: Schema, b: Schema) -> bool:
    return compatible_with(a, b) and compatible_with(b, a)


def _sub(sa: Schema, ta, sb: Schema, tb, seen: Set[Tuple[int, int]]) -> bool:
    da = sa.resolve(ta)
    db = sb.resolve(tb)
    key = (id(da), id(db))
    if key in seen:
        return True                       # assume compatible when a cycle repeats
    seen = seen | {key}
    if isinstance(da, Scalar) and isinstance(db, Scalar):
        return _scalar_sub(da, db)
    if isinstance(da, Record) and isinstance(db, Record):
        return _record_sub(sa, da, sb, db, seen)
    return False                          # a value vs an object — never compatible


def _scalar_sub(a: Scalar, b: Scalar) -> bool:
    if a.nullable and not b.nullable:
        return False
    if a.name == b.name:
        return True
    return a.name == "integer" and b.name == "number"   # the one subset relation


def _record_sub(sa: Schema, a: Record, sb: Schema, b: Record,
                seen: Set[Tuple[int, int]]) -> bool:
    # Every label A may emit must be allowed by B, with a cardinality range
    # B's covers and a type B accepts.
    for fa in a.fields:
        if fa.max == 0:
            continue                      # A never emits this label
        fb = b.field(fa.label)
        if fb is None:
            return False                  # B is closed and has no such field
        if not (fb.min <= fa.min and _le(fa.max, fb.max)):
            return False                  # [fa.min,fa.max] not a subset of B's range
        if not _sub(sa, fa.type, sb, fb.type, seen):
            return False
    # Every label B *requires* must be guaranteed by A.
    for fb in b.fields:
        if fb.min >= 1:
            fa = a.field(fb.label)
            if fa is None or fa.min < fb.min:
                return False
    return True


def _le(x: Optional[int], y: Optional[int]) -> bool:
    """x <= y, treating None as +infinity (unbounded max)."""
    if y is None:
        return True
    if x is None:
        return False
    return x <= y


# ---------------------------------------------------------------------------
# normalize — merge structurally identical named records
# ---------------------------------------------------------------------------

def normalize(s: Schema) -> Schema:
    groups: Dict[tuple, List[str]] = {}
    for name, rec in s.env.items():
        groups.setdefault(_struct_key(rec), []).append(name)
    rep: Dict[str, str] = {}
    for names in groups.values():
        keep = sorted(names)[0]
        for n in names:
            rep[n] = keep
    new_env: Dict[str, Any] = {}
    for name, rec in s.env.items():
        if rep[name] == name:
            new_env[name] = _remap(rec, rep)
    new_root = Ref(rep.get(s.root.name, s.root.name))
    return Schema(new_root, new_env)


def _struct_key(rec: Record) -> tuple:
    fields = tuple((f.label, f.min, f.max, _type_key(f.type)) for f in rec.fields)
    return ("record", fields)


def _type_key(t) -> tuple:
    if isinstance(t, Ref):
        return ("ref", t.name)
    return ("scalar", t.name, t.nullable)


def _remap(rec: Record, rep: Dict[str, str]) -> Record:
    return Record([Field(f.label, _remap_type(f.type, rep), f.min, f.max)
                   for f in rec.fields])


def _remap_type(t, rep: Dict[str, str]):
    if isinstance(t, Ref):
        return Ref(rep.get(t.name, t.name))
    return t
