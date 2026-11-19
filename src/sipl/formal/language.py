from __future__ import annotations

from sipl.formal.grammar import Grammar, Rule, is_nonterminal


def concatenations(rhs: Rule, words: dict[str, set[str]], max_length: int) -> set[str]:
    results = {""}
    for symbol in rhs:
        options = words.get(symbol, set()) if is_nonterminal(symbol) else {symbol}
        results = {a + b for a in results for b in options if len(a + b) <= max_length}
        if not results:
            break
    return results


def language_up_to(grammar: Grammar, max_length: int) -> set[str]:
    words: dict[str, set[str]] = {nt: set() for nt in grammar.nonterminals()}
    changed = True
    while changed:
        changed = False
        for lhs, rhs in grammar.all_rules():
            new = concatenations(rhs, words, max_length) - words[lhs]
            if new:
                words[lhs] |= new
                changed = True
    return words[grammar.start]
