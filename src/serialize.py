"""Serializers — render a canonical Data Tree back out to a concrete syntax.

These are the inverse of the loaders in :mod:`formats`.  Together they make the
Data Tree a **format-neutral hub**: parse one syntax into a Data Tree and emit
another from it.

    from src import tree_from_json, to_toml
    toml_text = to_toml(tree_from_json('{"name": "Ann", "tags": ["x", "y"]}'))

The canonical model is effectively the JSON data model (record / list / scalar
over string·number·bool·null).  Each target syntax is a projection of it:

* **JSON / YAML** — full coverage.
* **TOML** — a *partial* projection: TOML has no null value and its top level
  must be a table (object).  Emitting a tree that violates these raises a clear
  ``SerializationError`` rather than producing invalid TOML.

Round-trip fidelity comes from each scalar d-node's ``vdom`` type hint (attached
by the loaders), so the integer ``1`` re-emits as ``1`` while the string ``"1"``
re-emits as ``"1"``.
"""

from __future__ import annotations
from typing import Any

from .data_tree import DataTree
from .content_model import KIND_MAP, KIND_SEQUENCE, KIND_SCALAR
from .vdom import VDom


class SerializationError(ValueError):
    """Raised when a Data Tree cannot be represented in the target syntax."""


# ===========================================================================
# Data Tree  ->  Python object   (the canonical hub)
# ===========================================================================

def tree_to_python(tree: DataTree) -> Any:
    """Reconstruct a typed Python value (dict/list/scalar) from a Data Tree.

    The inverse of :func:`formats.tree_from_python`.  Scalar values are converted
    back to their Python type using each node's ``vdom`` hint; nodes without a
    hint (e.g. hand-built trees) fall back to a best-effort interpretation of the
    string value.
    """
    def _node_kind(node_id: Any) -> str:
        n = tree.node(node_id)
        if n.kind is not None:
            return n.kind
        edges = tree.child_edges(node_id)
        if not edges:
            return KIND_SCALAR
        # heuristic: all edges sharing one label ⇒ list, else record
        labels = [e.symbol for e in edges]
        return KIND_SEQUENCE if len(set(labels)) <= 1 and labels and labels[0] == "[]" \
            else KIND_MAP

    def _build(node_id: Any) -> Any:
        kind = _node_kind(node_id)
        if kind == KIND_MAP:
            out = {}
            for e in tree.child_edges(node_id):
                out[e.symbol] = _build(e.child_id)
            return out
        if kind == KIND_SEQUENCE:
            return [_build(e.child_id) for e in tree.child_edges(node_id)]
        return _scalar_to_python(tree.node(node_id))

    return _build(tree.root_id)


def _scalar_to_python(node) -> Any:
    vd = getattr(node, "vdom", None)
    value = node.value
    if vd is not None:
        if not vd.kinds:                      # null / pure-null domain
            return None
        kind = next(iter(vd.kinds)) if len(vd.kinds) == 1 else None
        if kind == VDom.BOOL:
            return str(value).lower() == "true"
        if kind == VDom.INTS:
            return int(value)
        if kind == VDom.DECS:
            return float(value)
        if kind == VDom.STRS:
            return value
        # union or enum: fall through to best-effort below
    return _coerce_unhinted(value)


def _coerce_unhinted(value: str) -> Any:
    if value == "":
        return ""
    low = value.lower()
    if low in ("true", "false"):
        return low == "true"
    try:
        return int(value)
    except (ValueError, TypeError):
        pass
    try:
        return float(value)
    except (ValueError, TypeError):
        pass
    return value


# ===========================================================================
# Concrete emitters
# ===========================================================================

def to_json(tree: DataTree, *, indent: int = None, sort_keys: bool = False) -> str:
    """Serialize a Data Tree to a JSON string."""
    import json
    return json.dumps(tree_to_python(tree), indent=indent, sort_keys=sort_keys,
                      ensure_ascii=False)


def to_yaml(tree: DataTree, *, sort_keys: bool = False) -> str:
    """Serialize a Data Tree to a YAML string (requires PyYAML)."""
    try:
        import yaml
    except ImportError as exc:  # pragma: no cover
        raise ImportError("PyYAML is required for YAML output: pip install pyyaml") from exc
    return yaml.safe_dump(tree_to_python(tree), sort_keys=sort_keys,
                          allow_unicode=True, default_flow_style=False)


def to_toml(tree: DataTree) -> str:
    """Serialize a Data Tree to a TOML string (requires ``tomli_w``).

    Raises :class:`SerializationError` if the tree cannot be a valid TOML
    document: the top level must be a table (object), and TOML has no null value.
    """
    try:
        import tomli_w
    except ImportError as exc:  # pragma: no cover
        raise ImportError("tomli_w is required for TOML output: pip install tomli_w") from exc

    obj = tree_to_python(tree)
    if not isinstance(obj, dict):
        raise SerializationError(
            "TOML documents must have a table (object) at the top level; "
            f"got {type(obj).__name__}.")
    _check_no_null(obj, "$")
    return tomli_w.dumps(obj)


def _check_no_null(obj: Any, path: str) -> None:
    if obj is None:
        raise SerializationError(
            f"TOML has no null value; cannot serialize null at {path}.")
    if isinstance(obj, dict):
        for k, v in obj.items():
            _check_no_null(v, f"{path}.{k}")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            _check_no_null(v, f"{path}[{i}]")
