"""Value Domain (VDom) — constrains the data values stored in d-nodes.

Pre-defined named domains mirror the XSD built-in types used in the paper.
"""

from __future__ import annotations
from typing import Optional, Set, Any


class VDom:
    """
    A value domain is a set of acceptable string values for a d-node.

    Named built-in domains:
        STRS  — all strings (universal, maps to xs:string / xs:anySimpleType)
        INTS  — integer strings (xs:int / xs:integer)
        DECS  — decimal strings (xs:decimal)
        NULL  — only the null/empty value ε (used for complex-type nodes)

    Custom finite domains can be supplied via the `values` parameter.
    """

    STRS = "STRS"
    INTS = "INTS"
    DECS = "DECS"
    NULL = "NULL"

    _NAMED = {STRS, INTS, DECS, NULL}

    def __init__(self, kind: str = STRS, values: Optional[Set[str]] = None) -> None:
        if kind not in self._NAMED and values is None:
            raise ValueError(f"Unknown domain kind {kind!r}; supply values= for custom domains")
        self.kind = kind
        self.values = frozenset(values) if values is not None else None

    # ------------------------------------------------------------------
    # Membership
    # ------------------------------------------------------------------

    def contains(self, value: str) -> bool:
        if self.kind == self.STRS:
            return True
        if self.kind == self.NULL:
            return value in ("", None)
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
        # custom finite set
        return value in (self.values or set())

    # ------------------------------------------------------------------
    # Subset relationship   (VDom(q) ⊆ VDom(q')  required by SubschemaSA)
    # ------------------------------------------------------------------

    def is_subset_of(self, other: "VDom") -> bool:
        if other.kind == self.STRS:
            return True  # STRS is universal
        if self.kind == other.kind:
            if self.values is None and other.values is None:
                return True
            if self.values is not None and other.values is not None:
                return self.values <= other.values
            # named same kind with no explicit value sets → equal
            return self.values is None  # both None case handled above
        if self.kind == self.NULL:
            return other.contains("")
        if self.kind == self.INTS and other.kind == self.DECS:
            return True  # every integer is also a decimal
        # finite ⊆ named
        if self.values is not None:
            return all(other.contains(v) for v in self.values)
        return False

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
    def null() -> "VDom":
        return VDom(VDom.NULL)

    @staticmethod
    def finite(*values: str) -> "VDom":
        return VDom("CUSTOM", set(values))

    # ------------------------------------------------------------------
    # Dunder
    # ------------------------------------------------------------------

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, VDom):
            return False
        return self.kind == other.kind and self.values == other.values

    def __hash__(self) -> int:
        return hash((self.kind, self.values))

    def __repr__(self) -> str:
        if self.values is not None:
            return f"VDom({{{', '.join(sorted(self.values))}}})"
        return f"VDom({self.kind})"
