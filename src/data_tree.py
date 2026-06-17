"""Data Tree (DT) — Definition 1 from the paper.

A DT is a 7-tuple (N, E, Y, n0, CEdges, Val, Sym) where:
    N       finite set of d-nodes
    E       finite set of d-edges (ordered pairs)
    Y       set of edge symbols
    n0      root d-node
    CEdges  N → E*   ordered child-edge sequence for each d-node
    Val     N → V    data value of each d-node (empty string = null/ε)
    Sym     E → Y    symbol labelling each d-edge
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional, Tuple


class DNode:
    """A data node storing a value."""

    def __init__(self, node_id: Any, value: str = "") -> None:
        self.node_id = node_id
        self.value = value  # "" represents ε (null value)

    def __repr__(self) -> str:
        v = repr(self.value) if self.value else "ε"
        return f"DNode({self.node_id}, {v})"


class DEdge:
    """A data edge connecting parent and child d-nodes, carrying a symbol."""

    def __init__(self, edge_id: Any, parent_id: Any, child_id: Any, symbol: str) -> None:
        self.edge_id = edge_id
        self.parent_id = parent_id
        self.child_id = child_id
        self.symbol = symbol

    def __repr__(self) -> str:
        return f"DEdge({self.edge_id}: {self.parent_id} -[{self.symbol}]-> {self.child_id})"


class DataTree:
    """
    Data Tree (DT) — tree-form data model.

    Nodes are accessed by their node_id; edges by edge_id.
    The ordered child-edge sequence is maintained per node.
    """

    def __init__(self, root_id: Any = 0, root_value: str = "") -> None:
        self._nodes: Dict[Any, DNode] = {}
        self._edges: Dict[Any, DEdge] = {}
        self._child_edges: Dict[Any, List[Any]] = {}  # node_id → ordered list of edge_ids
        self._edge_counter = 0

        root = DNode(root_id, root_value)
        self._nodes[root_id] = root
        self._child_edges[root_id] = []
        self.root_id = root_id

    # ------------------------------------------------------------------
    # Construction helpers
    # ------------------------------------------------------------------

    def add_node(self, node_id: Any, value: str = "") -> DNode:
        n = DNode(node_id, value)
        self._nodes[node_id] = n
        self._child_edges[node_id] = []
        return n

    def add_edge(
        self,
        parent_id: Any,
        child_id: Any,
        symbol: str,
        edge_id: Optional[Any] = None,
    ) -> DEdge:
        if edge_id is None:
            edge_id = self._edge_counter
            self._edge_counter += 1
        e = DEdge(edge_id, parent_id, child_id, symbol)
        self._edges[edge_id] = e
        self._child_edges[parent_id].append(edge_id)
        return e

    def add_child(
        self,
        parent_id: Any,
        child_id: Any,
        symbol: str,
        child_value: str = "",
    ) -> Tuple[DNode, DEdge]:
        """Convenience: create child node and edge in one call."""
        n = self.add_node(child_id, child_value)
        e = self.add_edge(parent_id, child_id, symbol)
        return n, e

    # ------------------------------------------------------------------
    # Accessors (CEdges, Val, Sym)
    # ------------------------------------------------------------------

    def node(self, node_id: Any) -> DNode:
        return self._nodes[node_id]

    def edge(self, edge_id: Any) -> DEdge:
        return self._edges[edge_id]

    def child_edges(self, node_id: Any) -> List[DEdge]:
        """CEdges(n) — ordered list of child d-edges."""
        return [self._edges[eid] for eid in self._child_edges[node_id]]

    def child_symbol_sequence(self, node_id: Any) -> List[str]:
        """CSeq(n) — the symbol sequence of child edges."""
        return [e.symbol for e in self.child_edges(node_id)]

    def val(self, node_id: Any) -> str:
        """Val(n)."""
        return self._nodes[node_id].value

    def sym(self, edge_id: Any) -> str:
        """Sym(e)."""
        return self._edges[edge_id].symbol

    def nodes(self) -> List[DNode]:
        return list(self._nodes.values())

    def edges(self) -> List[DEdge]:
        return list(self._edges.values())

    def symbols(self) -> set:
        """Y — set of all symbols on d-edges."""
        return {e.symbol for e in self._edges.values()}

    # ------------------------------------------------------------------
    # Pretty printing
    # ------------------------------------------------------------------

    def pretty(self, node_id: Optional[Any] = None, indent: int = 0) -> str:
        if node_id is None:
            node_id = self.root_id
        n = self._nodes[node_id]
        lines = ["  " * indent + f"[{node_id}:{n.value!r}]"]
        for e in self.child_edges(node_id):
            lines.append("  " * (indent + 1) + f"--{e.symbol}-->")
            lines.append(self.pretty(e.child_id, indent + 2))
        return "\n".join(lines)

    def __repr__(self) -> str:
        return f"DataTree(root={self.root_id}, nodes={len(self._nodes)}, edges={len(self._edges)})"
