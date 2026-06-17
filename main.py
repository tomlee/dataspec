"""
Demo: XML Schema Computations — Data Trees and Schema Automata
Based on: Lee & Cheung, CIKM 2010

Reproduces the key examples from the paper.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from src import (
    DataTree, SchemaAutomaton, HLang, VDom,
    make_useful_sa, minimize_sa, equivalent_sa, subschema_sa, extract_subschema,
)


def separator(title: str) -> None:
    print(f"\n{'='*60}")
    print(f"  {title}")
    print('='*60)


def build_quote_dt() -> DataTree:
    dt = DataTree("n0", "")
    dt.add_node("n1", ""); dt.add_node("n2", ""); dt.add_node("n3", "")
    dt.add_node("n4", "hPhone"); dt.add_node("n5", "499.9")
    dt.add_node("n6", "iMat"); dt.add_node("n7", "999.9")
    dt.add_edge("n0", "n1", "Quote")
    dt.add_edge("n1", "n2", "Line"); dt.add_edge("n1", "n3", "Line")
    dt.add_edge("n2", "n4", "Desc"); dt.add_edge("n2", "n5", "Price")
    dt.add_edge("n3", "n6", "Desc"); dt.add_edge("n3", "n7", "Price")
    return dt


def build_order_dt() -> DataTree:
    dt = DataTree("n0", "")
    dt.add_node("n1", ""); dt.add_node("n2", ""); dt.add_node("n3", "")
    dt.add_node("n4", "2"); dt.add_node("n5", "hPhone"); dt.add_node("n6", "499.9")
    dt.add_edge("n0", "n1", "Order")
    dt.add_edge("n1", "n2", "Line")
    dt.add_edge("n2", "n3", "Product"); dt.add_edge("n2", "n4", "Qty")
    dt.add_edge("n3", "n5", "Desc"); dt.add_edge("n3", "n6", "Price")
    return dt


def build_sa1() -> SchemaAutomaton:
    null = VDom.null()
    sa = SchemaAutomaton("q0")
    sa.add_state("q0", HLang.parse("Quote|Order"), null)
    sa.add_state("q1", HLang.parse("Line+"), null)
    sa.add_state("q2", HLang.parse("Line+"), null)
    sa.add_state("q3", HLang.parse("Desc Price"), null)
    sa.add_state("q4", HLang.parse("Product Qty"), null)
    sa.add_state("q5", HLang.epsilon_lang(), VDom.strs())
    sa.add_state("q6", HLang.epsilon_lang(), VDom.decs())
    sa.add_state("q7", HLang.parse("Desc Price"), null)
    sa.add_state("q8", HLang.epsilon_lang(), VDom.ints())
    sa.add_transition("q0", "Quote", "q1"); sa.add_transition("q0", "Order", "q2")
    sa.add_transition("q1", "Line", "q3"); sa.add_transition("q2", "Line", "q4")
    sa.add_transition("q3", "Desc", "q5"); sa.add_transition("q3", "Price", "q6")
    sa.add_transition("q4", "Product", "q7"); sa.add_transition("q4", "Qty", "q8")
    sa.add_transition("q7", "Desc", "q5"); sa.add_transition("q7", "Price", "q6")
    return sa


def build_sa2() -> SchemaAutomaton:
    null = VDom.null()
    sa = SchemaAutomaton("q0")
    sa.add_state("q0", HLang.parse("Quote|Order"), null)
    sa.add_state("q1", HLang.parse("Line+"), null)
    sa.add_state("q2", HLang.parse("Line+"), null)
    sa.add_state("q4", HLang.parse("Product Qty"), null)
    sa.add_state("q5", HLang.epsilon_lang(), VDom.strs())
    sa.add_state("q6", HLang.epsilon_lang(), VDom.decs())
    sa.add_state("q8", HLang.epsilon_lang(), VDom.ints())
    sa.add_state("q9", HLang.parse("Desc Price"), null)
    sa.add_transition("q0", "Quote", "q1"); sa.add_transition("q0", "Order", "q2")
    sa.add_transition("q1", "Line", "q9"); sa.add_transition("q2", "Line", "q4")
    sa.add_transition("q9", "Desc", "q5"); sa.add_transition("q9", "Price", "q6")
    sa.add_transition("q4", "Product", "q9"); sa.add_transition("q4", "Qty", "q8")
    return sa


def build_sa3() -> SchemaAutomaton:
    null = VDom.null()
    sa = SchemaAutomaton("q0")
    sa.add_state("q0", HLang.parse("Quote"), null)
    sa.add_state("q1", HLang.parse("Line+"), null)
    sa.add_state("q9", HLang.parse("Desc Price"), null)
    sa.add_state("q5", HLang.epsilon_lang(), VDom.strs())
    sa.add_state("q6", HLang.epsilon_lang(), VDom.decs())
    sa.add_transition("q0", "Quote", "q1")
    sa.add_transition("q1", "Line", "q9")
    sa.add_transition("q9", "Desc", "q5"); sa.add_transition("q9", "Price", "q6")
    return sa


def main() -> None:
    quote_dt = build_quote_dt()
    order_dt = build_order_dt()
    sa1 = build_sa1()
    sa2 = build_sa2()
    sa3 = build_sa3()

    # -------------------------------------------------------
    separator("§4.2.1  SA Validation of Data Trees")
    # -------------------------------------------------------
    print(f"SA1 accepts Quote DT:  {sa1.accepts(quote_dt)}")   # True
    print(f"SA1 accepts Order DT:  {sa1.accepts(order_dt)}")   # True
    print(f"SA2 accepts Quote DT:  {sa2.accepts(quote_dt)}")   # True
    print(f"SA2 accepts Order DT:  {sa2.accepts(order_dt)}")   # True
    print(f"SA3 accepts Quote DT:  {sa3.accepts(quote_dt)}")   # True
    print(f"SA3 accepts Order DT:  {sa3.accepts(order_dt)}")   # False

    # -------------------------------------------------------
    separator("§5.1  Schema Minimization")
    # -------------------------------------------------------
    min_sa1 = minimize_sa(sa1)
    print(f"SA1 has {len(sa1.states)} states")
    print(f"Minimized SA1 has {len(min_sa1.states)} states")
    print(f"  (SA2 has {len(sa2.states)} states — q3 and q7 merged into q9)")
    print(f"Minimized SA1 still accepts Quote DT: {min_sa1.accepts(quote_dt)}")
    print(f"Minimized SA1 still accepts Order DT: {min_sa1.accepts(order_dt)}")

    # -------------------------------------------------------
    separator("§5.3  Schema Equivalence Testing")
    # -------------------------------------------------------
    print(f"SA1 ≡ SA2:  {equivalent_sa(sa1, sa2)}")   # True
    print(f"SA3 ≡ SA1:  {equivalent_sa(sa3, sa1)}")   # False

    # -------------------------------------------------------
    separator("§5.3.1  Subschema Testing")
    # -------------------------------------------------------
    r1 = subschema_sa(sa3, sa1)
    r2 = subschema_sa(sa3, sa2)
    r3 = subschema_sa(sa1, sa3)
    print(f"SA3 ⊆ SA1:  {r1.is_compatible}")   # True
    print(f"SA3 ⊆ SA2:  {r2.is_compatible}")   # True
    print(f"SA1 ⊆ SA3:  {r3.is_compatible}")   # False
    if not r3.is_compatible:
        print(f"  Reason: {r3}")

    # -------------------------------------------------------
    separator("§5.4  Subschema Extraction")
    # -------------------------------------------------------
    permitted = {"Quote", "Order", "Line", "Qty", "Desc", "Price"}
    print(f"Extracting from SA2, permitted symbols: {sorted(permitted)}")
    print(f"(Excluding 'Product' — mandatory for Order/Line content)")
    extracted = extract_subschema(sa2, permitted)
    print(f"Extracted SA has {len(extracted.states)} states")
    print(f"Extracted SA accepts Quote DT: {extracted.accepts(quote_dt)}")
    print(f"Extracted SA accepts Order DT: {extracted.accepts(order_dt)}")
    print(f"Extracted SA ≡ SA3: {equivalent_sa(extracted, sa3)}")

    # -------------------------------------------------------
    separator("HLang mandatory symbol demo")
    # -------------------------------------------------------
    h_line_plus = HLang.parse("Line+")
    h_line_star = HLang.parse("Line*")
    print(f"HLang('Line+').is_mandatory('Line') = {h_line_plus.is_mandatory('Line')}")  # True
    print(f"HLang('Line*').is_mandatory('Line') = {h_line_star.is_mandatory('Line')}")  # False

    print("\nDone.")


if __name__ == "__main__":
    main()
