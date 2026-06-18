"""Value Domain (VDom) — constrains the data values stored in d-nodes.

Named built-in domains mirror the common scalar types found across data
formats (XML simple types, JSON/YAML/TOML scalars):

    STRS  — any string                     (xs:string, JSON string)
    INTS  — integer values                 (xs:int, JSON/TOML integer)
    DECS  — decimal / floating values       (xs:decimal, JSON/TOML float)
    BOOL  — boolean values                  (xs:boolean, JSON/TOML bool)
    NULL  — only the null/empty value ε      (used for complex/map/seq nodes)

A domain may additionally be *nullable*, meaning it also admits the null value
(needed for JSON/YAML fields that are "string or null", etc.).  Custom finite
domains (enumerations) are supported via ``VDom.finite(...)``.
"""

from __future__ import annotations
from typing import Optional, Set


class VDom:
    STRS = "STRS"
    INTS = "INTS"
    DECS = "DECS"
    BOOL = "BOOL"
    NULL = "NULL"
    CUSTOM = "CUSTOM"

    _NAMED = {STRS, INTS, DECS, BOOL, NULL}

    # numeric generality ordering used by union()
    _NUMERIC = {INTS, DECS}

    def __init__(
        self,
        kind: str = STRS,
        values: Optional[Set[str]] = None,
        nullable: bool = False,
    ) -> None:
        if kind not in self._NAMED and kind != self.CUSTOM and values is None:
            raise ValueError(f"Unknown domain kind {kind!r}; supply values= for custom domains")
        self.kind = kind
        self.values = frozenset(values) if values is not None else None
        self.nullable = nullable

    # ------------------------------------------------------------------
    # Membership
    # ------------------------------------------------------------------

    def contains(self, value: str) -> bool:
        if self.nullable and value in ("", None):
            return True
        return self._base_contains(value)

    def _base_contains(self, value: str) -> bool:
        if self.kind == self.STRS:
            return True
        if self.kind == self.NULL:
            return value in ("", None)
        if self.kind == self.BOOL:
            return str(value).lower() in ("true", "false")
        if self.kind == self.INTS:
            try:
                int(value)
                return True
            except (ValueError, TypeError):
                return False
        if self.kind == self.DECS:
            try:
                float(value)
                return True
            except (ValueError, TypeError):
                return False
        return value in (self.values or set())

    # ------------------------------------------------------------------
    # Subset relationship   (VDom(q) ⊆ VDom(q')  required by SubschemaSA)
    # ------------------------------------------------------------------

    def is_subset_of(self, other: "VDom") -> bool:
        # nullability: if self admits null, other must too
        if self.nullable and not (other.nullable or other._base_contains("")):
            return False
        return self._base_subset(other)

    def _base_subset(self, other: "VDom") -> bool:
        if other.kind == self.STRS:
            return True  # STRS is universal
        if self.kind == self.NULL:
            return other._base_contains("")
        if self.values is not None:
            # finite domain ⊆ other iff every value is in other
            return all(other._base_contains(v) for v in self.values)
        if self.kind == other.kind:
            if other.values is None:
                return True
            return False  # named (infinite) ⊄ finite
        if self.kind == self.INTS and other.kind == self.DECS:
            return True  # every integer is also a decimal
        if self.kind == self.BOOL and other.values is not None:
            return {"true", "false"} <= {v.lower() for v in other.values}
        return False

    # ------------------------------------------------------------------
    # Generalisation — least domain covering both (used by schema inference)
    # ------------------------------------------------------------------

    @staticmethod
    def union(a: "VDom", b: "VDom") -> "VDom":
        nullable = a.nullable or b.nullable or a.kind == VDom.NULL or b.kind == VDom.NULL

        # treat NULL as contributing only nullability
        bases = [d for d in (a, b) if d.kind != VDom.NULL]
        if not bases:
            return VDom(VDom.NULL, nullable=True)
        if len(bases) == 1:
            base = bases[0]
            return VDom(base.kind, set(base.values) if base.values is not None else None,
                        nullable=nullable)

        x, y = bases
        # both finite custom -> union the value sets
        if x.values is not None and y.values is not None:
            return VDom(VDom.CUSTOM, set(x.values) | set(y.values), nullable=nullable)
        # numeric generalisation
        if x.kind in VDom._NUMERIC and y.kind in VDom._NUMERIC:
            kind = VDom.DECS if VDom.DECS in (x.kind, y.kind) else VDom.INTS
            return VDom(kind, nullable=nullable)
        if x.kind == y.kind and x.values is None and y.values is None:
            return VDom(x.kind, nullable=nullable)
        # fall back to the universal string domain
        return VDom(VDom.STRS, nullable=nullable)

    def as_nullable(self) -> "VDom":
        return VDom(self.kind, set(self.values) if self.values is not None else None, nullable=True)

    # ------------------------------------------------------------------
    # Pre-built singletons
    # ------------------------------------------------------------------

    @staticmethod
    def strs() -> "VDom":
        return VDom(VDom.STRS)

    @staticmethod
    def ints() -> "VDom":
        return VDom(VDom.INTS)

    @staticmethod
    def decs() -> "VDom":
        return VDom(VDom.DECS)

    @staticmethod
    def bool_() -> "VDom":
        return VDom(VDom.BOOL)

    @staticmethod
    def null() -> "VDom":
        return VDom(VDom.NULL)

    @staticmethod
    def finite(*values: str) -> "VDom":
        return VDom(VDom.CUSTOM, set(values))

    # ------------------------------------------------------------------
    # Dunder
    # ------------------------------------------------------------------

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, VDom):
            return False
        return (self.kind == other.kind
                and self.values == other.values
                and self.nullable == other.nullable)

    def __hash__(self) -> int:
        return hash((self.kind, self.values, self.nullable))

    def __repr__(self) -> str:
        suffix = "?" if self.nullable else ""
        if self.values is not None:
            return f"VDom({{{', '.join(sorted(self.values))}}}){suffix}"
        return f"VDom({self.kind}){suffix}"
