from __future__ import annotations

from sipl.formal.grammar import Grammar, is_nonterminal


def has_epsilon_rules(grammar: Grammar) -> bool:
    return any(not rhs for _, rhs in grammar.all_rules())


def has_unit_rules(grammar: Grammar) -> bool:
    return any(len(rhs) == 1 and is_nonterminal(rhs[0]) for _, rhs in grammar.all_rules())


def is_chomsky(grammar: Grammar) -> bool:
    start_on_right = any(grammar.start in rhs for _, rhs in grammar.all_rules())
    for lhs, rhs in grammar.all_rules():
        if not rhs:
            if lhs != grammar.start or start_on_right:
                return False
        elif len(rhs) == 1:
            if is_nonterminal(rhs[0]):
                return False
        elif len(rhs) == 2:
            if not all(is_nonterminal(s) for s in rhs):
                return False
        else:
            return False
    return True
