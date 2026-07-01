"""Field signature helpers for schema normalization and isomorphism detection."""

from __future__ import annotations

from typing import Tuple, Union

from ..schema import Record, Ref, Scalar


def local_signature(rec: Record) -> Tuple:
    """Compute the per-field (label, min, max, type-part) tuple for a record,
    WITHOUT ref target names. Type-part is ("scalar", name, nullable) for
    scalars and just ("ref",) for refs (target-blind, for partition and future
    isomorphism algorithms)."""
    return tuple(
        (f.label, f.min, f.max, _local_type_key(f.type))
        for f in rec.fields
    )


def struct_key(rec: Record) -> Tuple:
    """Compute the structural key for a record, INCLUDING ref target names.
    Used by normalize() to preserve today's exact behavior."""
    fields = tuple(
        (f.label, f.min, f.max, _type_key(f.type))
        for f in rec.fields
    )
    return ("record", fields)


def _local_type_key(t: Union[Ref, Scalar]) -> Tuple:
    """Type key WITHOUT ref target name (target-blind)."""
    if isinstance(t, Ref):
        return ("ref",)
    return ("scalar", t.name, t.nullable)


def _type_key(t: Union[Ref, Scalar]) -> Tuple:
    """Type key INCLUDING ref target name (preserves exact normalize behavior)."""
    if isinstance(t, Ref):
        return ("ref", t.name)
    return ("scalar", t.name, t.nullable)
