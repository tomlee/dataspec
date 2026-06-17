"""Schema Automaton (SA) — Definition 2 from the paper.

An SA is a 6-tuple (Q, X, q0, δ, HLang, VDom) where:
    Q       finite set of states (each representing an XSD type)
    X       finite set of symbols (element names)
    q0      initial state
    δ       Q × X → Q ∪ {⊥}   transition function (missing key = ⊥)
    HLang   Q → non-empty regular language over X
    VDom    Q → non-empty value domain
"""

from __future__ import annotations
from typing import Any, Dict, Optional, Set

from .hlang import HLang
from .vdom import VDom
from .data_tree import DataTree


_DEAD = None  # sentinel for ⊥ (dead state)


class SchemaAutomaton:
    """
    Schema Automaton — a deterministic automaton that validates Data Trees.

    States can be any hashable value (strings, ints, etc.).
    """

    def __init__(self, initial: Any) -> None:
        self.states: Set[Any] = {initial}
        self.symbols: Set[str] = set()
        self.initial: Any = initial
        # δ[state][symbol] = next_state  (absent = ⊥)
        self.delta: Dict[Any, Dict[str, Any]] = {initial: {}}
        self.hlang: Dict[Any, HLang] = {}
        self.vdom: Dict[Any, VDom] = {}

    # ------------------------------------------------------------------
    # Construction helpers
    # ------------------------------------------------------------------

    def add_state(
        self,
        state: Any,
        hlang: Optional[HLang] = None,
        vdom: Optional[VDom] = None,
    ) -> None:
        self.states.add(state)
        self.delta.setdefault(state, {})
        if hlang is not None:
            self.hlang[state] = hlang
        if vdom is not None:
            self.vdom[state] = vdom

    def set_hlang(self, state: Any, hlang: HLang) -> None:
        self.hlang[state] = hlang

    def set_vdom(self, state: Any, vdom: VDom) -> None:
        self.vdom[state] = vdom

    def add_transition(self, src: Any, symbol: str, dst: Any) -> None:
        self.symbols.add(symbol)
        self.delta.setdefault(src, {})[symbol] = dst

    def transition(self, state: Any, symbol: str) -> Optional[Any]:
        """δ(state, symbol) — returns None (⊥) if no transition defined."""
        return self.delta.get(state, {}).get(symbol, _DEAD)

    def get_hlang(self, state: Any) -> HLang:
        return self.hlang.get(state, HLang.epsilon_lang())

    def get_vdom(self, state: Any) -> VDom:
        return self.vdom.get(state, VDom.strs())

    # ------------------------------------------------------------------
    # Validation: SA accepts DT?  (Definition 3)
    # ------------------------------------------------------------------

    def accepts(self, tree: DataTree) -> bool:
        """Return True if this SA accepts the given DataTree."""
        def _check(node_id: Any, state: Any) -> bool:
            n = tree.node(node_id)
            # Condition 2: value must be in VDom(state)
            if not self.get_vdom(state).contains(n.value):
                return False
            # Condition 3a: child symbol sequence must be in HLang(state)
            cseq = tree.child_symbol_sequence(node_id)
            if not self.get_hlang(state).accepts(cseq):
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
        lines.append(f"  States: {sorted(str(s) for s in self.states)}")
        lines.append(f"  Symbols: {sorted(self.symbols)}")
        for q in sorted(str(s) for s in self.states):
            q_key = q  # states might be non-string; find original
            for orig in self.states:
                if str(orig) == q:
                    q_key = orig
                    break
            h = self.get_hlang(q_key)
            v = self.get_vdom(q_key)
            trans = self.delta.get(q_key, {})
            lines.append(f"  {q_key}: HLang={h!r}  VDom={v!r}  δ={trans}")
        return "\n".join(lines)

    def __repr__(self) -> str:
        return f"SchemaAutomaton(states={self.states}, initial={self.initial!r})"
