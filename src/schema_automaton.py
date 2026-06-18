"""Schema Automaton (SA) — Definition 2 from the paper, generalised to be
data-format agnostic.

An SA is a 6-tuple (Q, X, q0, δ, Content, VDom) where:
    Q        finite set of states (each representing a data type)
    X        finite set of symbols (element names / object keys / array marker)
    q0       initial state
    δ        Q × X → Q ∪ {⊥}   transition function (missing key = ⊥)
    Content  Q → ContentModel   permissible children of a node in this state
    VDom     Q → value domain   permissible scalar value of a node in this state

The only change from the original paper is that the per-state *horizontal
language* (HLang) is generalised to a ``ContentModel`` so the same automaton can
describe ordered (XML / arrays) and unordered (JSON / TOML / YAML maps) content.
An HLang is simply the ordered ``SequenceModel``; the rest of the machinery is
unchanged.
"""

from __future__ import annotations
from typing import Any, Dict, Optional, Set

from .content_model import ContentModel, ScalarModel
from .vdom import VDom
from .data_tree import DataTree


_DEAD = None  # sentinel for ⊥ (dead state)


class SchemaAutomaton:
    """A deterministic automaton that validates Data Trees of any data format."""

    def __init__(self, initial: Any) -> None:
        self.states: Set[Any] = {initial}
        self.symbols: Set[str] = set()
        self.initial: Any = initial
        # δ[state][symbol] = next_state  (absent = ⊥)
        self.delta: Dict[Any, Dict[str, Any]] = {initial: {}}
        self.content: Dict[Any, ContentModel] = {}
        self.vdom: Dict[Any, VDom] = {}

    # ------------------------------------------------------------------
    # Construction helpers
    # ------------------------------------------------------------------

    def add_state(
        self,
        state: Any,
        content: Optional[ContentModel] = None,
        vdom: Optional[VDom] = None,
    ) -> None:
        self.states.add(state)
        self.delta.setdefault(state, {})
        if content is not None:
            self.content[state] = content
        if vdom is not None:
            self.vdom[state] = vdom

    def set_content(self, state: Any, content: ContentModel) -> None:
        self.content[state] = content

    def set_vdom(self, state: Any, vdom: VDom) -> None:
        self.vdom[state] = vdom

    # Backward-compatible aliases (HLang is a ContentModel)
    set_hlang = set_content

    def add_transition(self, src: Any, symbol: str, dst: Any) -> None:
        self.symbols.add(symbol)
        self.delta.setdefault(src, {})[symbol] = dst

    def transition(self, state: Any, symbol: str) -> Optional[Any]:
        """δ(state, symbol) — returns None (⊥) if no transition defined."""
        return self.delta.get(state, {}).get(symbol, _DEAD)

    def get_content(self, state: Any) -> ContentModel:
        return self.content.get(state, ScalarModel())

    # Backward-compatible alias used by older call sites / tests
    get_hlang = get_content

    def get_vdom(self, state: Any) -> VDom:
        return self.vdom.get(state, VDom.strs())

    # ------------------------------------------------------------------
    # Validation: SA accepts DT?  (Definition 3, with optional kind check)
    # ------------------------------------------------------------------

    def accepts(self, tree: DataTree) -> bool:
        """Return True if this SA accepts the given DataTree."""
        def _check(node_id: Any, state: Any) -> bool:
            n = tree.node(node_id)
            content = self.get_content(state)

            # Optional structural-kind agreement (distinguishes empty map vs seq
            # vs scalar when the data tree carries kind information).
            if n.kind is not None and content.kind and n.kind != content.kind:
                return False

            # Condition 2: value must be in VDom(state)
            if not self.get_vdom(state).contains(n.value):
                return False

            # Condition 3a: child symbol sequence must be in Content(state)
            cseq = tree.child_symbol_sequence(node_id)
            if not content.accepts(cseq):
                return False

            # Condition 3b: each child must be accepted by δ(state, symbol)
            for edge in tree.child_edges(node_id):
                next_state = self.transition(state, edge.symbol)
                if next_state is _DEAD:
                    return False
                if not _check(edge.child_id, next_state):
                    return False
            return True

        return _check(tree.root_id, self.initial)

    # ------------------------------------------------------------------
    # Display
    # ------------------------------------------------------------------

    def describe(self) -> str:
        lines = [f"SchemaAutomaton(initial={self.initial!r})"]
        lines.append(f"  States:  {sorted(str(s) for s in self.states)}")
        lines.append(f"  Symbols: {sorted(self.symbols)}")
        for q in sorted(self.states, key=str):
            content = self.get_content(q)
            v = self.get_vdom(q)
            trans = self.delta.get(q, {})
            lines.append(f"  {q}: Content={content!r}  VDom={v!r}  δ={trans}")
        return "\n".join(lines)

    def __repr__(self) -> str:
        return f"SchemaAutomaton(states={len(self.states)}, initial={self.initial!r})"
