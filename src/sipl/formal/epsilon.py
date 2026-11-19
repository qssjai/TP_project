from __future__ import annotations

from collections.abc import Iterator
from itertools import combinations

from sipl.formal.grammar import EPSILON, Grammar, Rule, format_rule
from sipl.formal.outcome import Outcome


def nullable_symbols(grammar: Grammar) -> set[str]:
    nullable: set[str] = set()
    changed = True
    while changed:
        changed = False
        for lhs, rhs in grammar.all_rules():
            if lhs not in nullable and all(s in nullable for s in rhs):
                nullable.add(lhs)
                changed = True
    return nullable


def _without_occurrences(rhs: Rule, symbol: str) -> Iterator[Rule]:
    positions = [i for i, s in enumerate(rhs) if s == symbol]
    for size in range(1, len(positions) + 1):
        for removed in combinations(positions, size):
            yield tuple(s for i, s in enumerate(rhs) if i not in removed)


def remove_epsilon_rules(grammar: Grammar) -> Outcome:
    order = grammar.nonterminals()
    nullable = nullable_symbols(grammar)
    if not nullable:
        return Outcome(grammar.copy(), ["ε-нетерміналів немає, правила не змінюються. ε ∉ L(G)."])

    steps = ["ε-нетермінали: " + ", ".join(nt for nt in order if nt in nullable) + "."]
    work = grammar.copy()
    for symbol in order:
        if symbol not in nullable:
            continue
        added = []
        for lhs, rhs in list(work.all_rules()):
            for variant in _without_occurrences(rhs, symbol):
                if variant and variant != (lhs,) and work.add_rule(lhs, variant):
                    added.append(format_rule(lhs, variant))
        line = f"Розглядаємо {symbol}: "
        line += "додаємо правила " + "; ".join(added) if added else "нових правил не додаємо"
        if () in work.alternatives(symbol):
            work.remove_rule(symbol, ())
            line += f"; видаляємо {symbol} → {EPSILON}"
        steps.append(line + ".")

    empty_word = grammar.start in nullable
    if empty_word:
        steps.append(
            f"Аксіома {grammar.start} є ε-нетерміналом, тобто ε ∈ L(G): "
            f"одержана граматика породжує L(G) \\ {{ε}}."
        )
    else:
        steps.append("ε ∉ L(G), одержана граматика еквівалентна початковій.")
    return Outcome(work, steps, empty_word)
