"""NFA/DFA engine used to represent and test horizontal languages (HLangs)."""

from __future__ import annotations
from typing import Dict, FrozenSet, Optional, Set, List, Tuple

_EPSILON = None  # sentinel for epsilon transitions


class NFA:
    """Non-deterministic Finite Automaton with epsilon transitions."""

    def __init__(self) -> None:
        self._counter: int = 0
        self.states: Set[int] = set()
        self.alphabet: Set[str] = set()
        # transitions[state][symbol or None] = set of destination states
        self.transitions: Dict[int, Dict[Optional[str], Set[int]]] = {}
        self.start: int = 0
        self.accept: Set[int] = set()

    def new_state(self) -> int:
        s = self._counter
        self._counter += 1
        self.states.add(s)
        self.transitions[s] = {}
        return s

    def add_trans(self, src: int, sym: Optional[str], dst: int) -> None:
        if sym is not None:
            self.alphabet.add(sym)
        self.transitions[src].setdefault(sym, set()).add(dst)

    def e_closure(self, states: Set[int]) -> FrozenSet[int]:
        closure = set(states)
        stack = list(states)
        while stack:
            s = stack.pop()
            for t in self.transitions.get(s, {}).get(None, set()):
                if t not in closure:
                    closure.add(t)
                    stack.append(t)
        return frozenset(closure)

    def move(self, states: FrozenSet[int], sym: str) -> FrozenSet[int]:
        result: Set[int] = set()
        for s in states:
            result |= self.transitions.get(s, {}).get(sym, set())
        return frozenset(result)

    def to_dfa(self) -> "DFA":
        """Subset construction: NFA → DFA."""
        start_set = self.e_closure({self.start})
        id_map: Dict[FrozenSet[int], int] = {}
        ctr = [0]

        def get_id(fs: FrozenSet[int]) -> int:
            if fs not in id_map:
                id_map[fs] = ctr[0]
                ctr[0] += 1
            return id_map[fs]

        dfa = DFA(frozenset(self.alphabet))
        dfa.start = get_id(start_set)

        worklist = [start_set]
        visited: Set[FrozenSet[int]] = {start_set}

        while worklist:
            cur = worklist.pop()
            cur_id = get_id(cur)
            if cur & self.accept:
                dfa.accept.add(cur_id)
            for sym in self.alphabet:
                nxt = self.e_closure(self.move(cur, sym))
                if not nxt:
                    continue
                nxt_id = get_id(nxt)
                dfa.transitions.setdefault(cur_id, {})[sym] = nxt_id
                if nxt not in visited:
                    visited.add(nxt)
                    worklist.append(nxt)

        dfa.states = set(id_map.values())
        return dfa


# ---------------------------------------------------------------------------
# Thompson construction helpers
# ---------------------------------------------------------------------------

def _merge(n1: NFA, n2: NFA) -> Tuple[NFA, int]:
    """Copy both NFAs into a fresh NFA. Returns (merged, offset_for_n2_states)."""
    n = NFA()
    # Copy n1 as-is
    for s in n1.states:
        n.states.add(s)
        n.transitions[s] = {}
        for sym, dsts in n1.transitions.get(s, {}).items():
            n.transitions[s][sym] = set(dsts)
            if sym is not None:
                n.alphabet.add(sym)
    n._counter = n1._counter

    # Copy n2 with offset
    offset = n1._counter
    for s in n2.states:
        ns = s + offset
        n.states.add(ns)
        n.transitions[ns] = {}
        for sym, dsts in n2.transitions.get(s, {}).items():
            n.transitions[ns][sym] = {d + offset for d in dsts}
            if sym is not None:
                n.alphabet.add(sym)
    n._counter += n2._counter
    return n, offset


def nfa_symbol(sym: str) -> NFA:
    n = NFA()
    s0, s1 = n.new_state(), n.new_state()
    n.start = s0
    n.accept = {s1}
    n.add_trans(s0, sym, s1)
    return n


def nfa_epsilon() -> NFA:
    n = NFA()
    s = n.new_state()
    n.start = s
    n.accept = {s}
    return n


def nfa_union(n1: NFA, n2: NFA) -> NFA:
    n, off = _merge(n1, n2)
    ns = n.new_state()
    na = n.new_state()
    n.start = ns
    n.accept = {na}
    n.add_trans(ns, None, n1.start)
    n.add_trans(ns, None, n2.start + off)
    for a in n1.accept:
        n.add_trans(a, None, na)
    for a in n2.accept:
        n.add_trans(a + off, None, na)
    return n


def nfa_concat(n1: NFA, n2: NFA) -> NFA:
    n, off = _merge(n1, n2)
    for a in n1.accept:
        n.add_trans(a, None, n2.start + off)
    n.start = n1.start
    n.accept = {a + off for a in n2.accept}
    return n


def nfa_star(n1: NFA) -> NFA:
    n = NFA()
    # re-use n1's structure by copying
    for s in n1.states:
        n.states.add(s)
        n.transitions[s] = {}
        for sym, dsts in n1.transitions.get(s, {}).items():
            n.transitions[s][sym] = set(dsts)
            if sym is not None:
                n.alphabet.add(sym)
    n._counter = n1._counter

    ns = n.new_state()
    na = n.new_state()
    n.start = ns
    n.accept = {na}
    n.add_trans(ns, None, n1.start)
    n.add_trans(ns, None, na)
    for a in n1.accept:
        n.add_trans(a, None, n1.start)
        n.add_trans(a, None, na)
    return n


def nfa_plus(n1: NFA) -> NFA:
    # n1 n1*
    from copy import deepcopy
    n1_copy = deepcopy(n1)
    return nfa_concat(n1, nfa_star(n1_copy))


def nfa_optional(n1: NFA) -> NFA:
    return nfa_union(n1, nfa_epsilon())


def nfa_repeat(n1: NFA, lo: int, hi: Optional[int]) -> NFA:
    """Build n1{lo,hi}. hi=None means unlimited."""
    from copy import deepcopy
    # Build lo copies concatenated
    parts = [deepcopy(n1) for _ in range(lo)]
    result = parts[0] if parts else nfa_epsilon()
    for p in parts[1:]:
        result = nfa_concat(result, p)
    if hi is None:
        result = nfa_concat(result, nfa_star(deepcopy(n1)))
    else:
        for _ in range(hi - lo):
            result = nfa_concat(result, nfa_optional(deepcopy(n1)))
    return result


# ---------------------------------------------------------------------------
# DFA
# ---------------------------------------------------------------------------

class DFA:
    """Deterministic Finite Automaton over a string alphabet."""

    def __init__(self, alphabet: FrozenSet[str] = frozenset()) -> None:
        self.states: Set[int] = set()
        self.alphabet: FrozenSet[str] = alphabet
        self.transitions: Dict[int, Dict[str, int]] = {}
        self.start: int = 0
        self.accept: Set[int] = set()

    def accepts(self, word: List[str]) -> bool:
        state: Optional[int] = self.start
        for sym in word:
            state = self.transitions.get(state, {}).get(sym)
            if state is None:
                return False
        return state in self.accept

    def make_complete(self, dead: int = -1, alphabet: Optional[FrozenSet[str]] = None) -> "DFA":
        """Return equivalent complete DFA with explicit dead state.

        ``alphabet`` may be wider than this DFA's own alphabet; missing symbols
        route to the dead state.  This matters when comparing two DFAs over
        different alphabets (e.g. subset/complement testing).
        """
        alpha = self.alphabet if alphabet is None else frozenset(alphabet)
        new = DFA(alpha)
        new.states = set(self.states) | {dead}
        new.start = self.start
        new.accept = set(self.accept)
        for s in new.states:
            new.transitions[s] = {}
            for sym in alpha:
                dst = self.transitions.get(s, {}).get(sym, dead)
                new.transitions[s][sym] = dst
        return new

    def complement(self, alphabet: Optional[FrozenSet[str]] = None) -> "DFA":
        c = self.make_complete(alphabet=alphabet)
        c.accept = c.states - c.accept
        return c

    def intersection(self, other: "DFA") -> "DFA":
        alpha = frozenset(self.alphabet | other.alphabet)
        DEAD_A, DEAD_B = -1, -2
        pair_map: Dict[Tuple[int, int], int] = {}
        ctr = [0]

        def get_id(p: Tuple[int, int]) -> int:
            if p not in pair_map:
                pair_map[p] = ctr[0]
                ctr[0] += 1
            return pair_map[p]

        result = DFA(alpha)
        init = (self.start, other.start)
        result.start = get_id(init)

        worklist = [init]
        visited: Set[Tuple[int, int]] = {init}

        while worklist:
            p = worklist.pop()
            s1, s2 = p
            pid = get_id(p)
            result.states.add(pid)
            if s1 in self.accept and s2 in other.accept:
                result.accept.add(pid)
            for sym in alpha:
                n1 = self.transitions.get(s1, {}).get(sym, DEAD_A)
                n2 = other.transitions.get(s2, {}).get(sym, DEAD_B)
                np = (n1, n2)
                result.transitions.setdefault(pid, {})[sym] = get_id(np)
                if np not in visited:
                    visited.add(np)
                    worklist.append(np)
        return result

    def is_empty(self) -> bool:
        if not self.accept:
            return True
        visited: Set[int] = set()
        stack = [self.start]
        while stack:
            s = stack.pop()
            if s in visited:
                continue
            visited.add(s)
            if s in self.accept:
                return False
            for dst in self.transitions.get(s, {}).values():
                stack.append(dst)
        return True

    def is_subset_of(self, other: "DFA") -> bool:
        """L(self) ⊆ L(other)?"""
        # Complement must be taken over the *combined* alphabet, otherwise
        # symbols only in `self` are invisible to `other`'s complement and
        # counterexamples using them are missed.
        alpha = frozenset(self.alphabet | other.alphabet)
        comp = other.complement(alphabet=alpha)
        return self.intersection(comp).is_empty()

    def language_equals(self, other: "DFA") -> bool:
        return self.is_subset_of(other) and other.is_subset_of(self)

    def minimize(self) -> "DFA":
        """Hopcroft DFA minimization. Returns minimal equivalent DFA."""
        complete = self.make_complete()
        if not complete.states:
            return complete

        accept = frozenset(complete.accept)
        non_accept = frozenset(complete.states - complete.accept)

        partition: Set[FrozenSet[int]] = set()
        if accept:
            partition.add(accept)
        if non_accept:
            partition.add(non_accept)

        worklist: Set[FrozenSet[int]] = set()
        if accept:
            worklist.add(accept)
        if non_accept:
            worklist.add(non_accept)

        while worklist:
            splitter = worklist.pop()
            for sym in complete.alphabet:
                X = frozenset(
                    s for s in complete.states
                    if complete.transitions.get(s, {}).get(sym) in splitter
                )
                if not X:
                    continue
                new_partition: Set[FrozenSet[int]] = set()
                for block in partition:
                    inter = block & X
                    diff = block - X
                    if inter and diff:
                        new_partition.add(inter)
                        new_partition.add(diff)
                        if block in worklist:
                            worklist.discard(block)
                            worklist.add(inter)
                            worklist.add(diff)
                        else:
                            worklist.add(inter if len(inter) <= len(diff) else diff)
                    else:
                        new_partition.add(block)
                partition = new_partition

        block_of: Dict[int, FrozenSet[int]] = {}
        for block in partition:
            for s in block:
                block_of[s] = block

        block_list = list(partition)
        block_id = {b: i for i, b in enumerate(block_list)}

        result = DFA(complete.alphabet)
        result.states = set(range(len(block_list)))
        result.start = block_id[block_of[complete.start]]
        result.accept = {block_id[b] for b in partition if any(s in complete.accept for s in b)}

        for block in partition:
            rep = next(iter(block))
            bid = block_id[block]
            result.transitions[bid] = {}
            for sym in complete.alphabet:
                dst = complete.transitions.get(rep, {}).get(sym)
                if dst is not None:
                    dst_block = block_of.get(dst)
                    if dst_block is not None:
                        result.transitions[bid][sym] = block_id[dst_block]
        return result

    def canonical_key(self) -> tuple:
        """Return a hashable canonical form (BFS-order relabelling of minimized DFA)."""
        dfa = self.minimize()
        mapping: Dict[int, int] = {}
        order: List[int] = []
        queue = [dfa.start]
        visited: Set[int] = {dfa.start}
        while queue:
            s = queue.pop(0)
            mapping[s] = len(order)
            order.append(s)
            for sym in sorted(dfa.alphabet):
                dst = dfa.transitions.get(s, {}).get(sym)
                if dst is not None and dst not in visited:
                    visited.add(dst)
                    queue.append(dst)

        trans_key = frozenset(
            (mapping[s], sym, mapping[d])
            for s, tmap in dfa.transitions.items()
            for sym, d in tmap.items()
            if s in mapping and d in mapping
        )
        accept_key = frozenset(mapping[s] for s in dfa.accept if s in mapping)
        return (frozenset(dfa.alphabet), trans_key, accept_key)
