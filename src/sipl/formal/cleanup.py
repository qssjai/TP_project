from __future__ import annotations

from sipl.formal.grammar import Grammar, format_rule, is_nonterminal
from sipl.formal.outcome import Outcome, format_set, subscript


def reachable_sets(grammar: Grammar) -> list[set[str]]:
    current = {grammar.start}
    history = [current]
    while True:
        following = set(current)
        for lhs in current:
            for rhs in grammar.alternatives(lhs):
                following.update(s for s in rhs if is_nonterminal(s))
        if following == current:
            return history
        history.append(following)
        current = following


def productive_sets(grammar: Grammar) -> list[set[str]]:
    current = {lhs for lhs, rhs in grammar.all_rules() if not any(is_nonterminal(s) for s in rhs)}
    history = [current]
    while True:
        following = set(current)
        for lhs, rhs in grammar.all_rules():
            if all(not is_nonterminal(s) or s in current for s in rhs):
                following.add(lhs)
        if following == current:
            return history
        history.append(following)
        current = following


def remove_useless(grammar: Grammar) -> Outcome:
    order = grammar.nonterminals()
    steps: list[str] = []

    productive_history = productive_sets(grammar)
    for index, found in enumerate(productive_history):
        steps.append(f"Pr{subscript(index)} = {format_set(found, order)}")
    productive = productive_history[-1]

    if grammar.start not in productive:
        steps.append(f"Аксіома {grammar.start} непродуктивна, мова порожня, усі правила видаляються.")
        return Outcome(Grammar(grammar.start), steps)

    productive_grammar = Grammar(grammar.start)
    dropped = []
    for lhs, rhs in grammar.all_rules():
        if lhs in productive and all(not is_nonterminal(s) or s in productive for s in rhs):
            productive_grammar.add_rule(lhs, rhs)
        else:
            dropped.append(format_rule(lhs, rhs))
    unproductive = [nt for nt in order if nt not in productive]
    if unproductive:
        steps.append(
            f"Непродуктивні нетермінали: {', '.join(unproductive)}. "
            f"Видаляємо їх та правила, де вони трапляються: {'; '.join(dropped)}."
        )
    else:
        steps.append("Непродуктивних нетерміналів немає.")

    reachable_history = reachable_sets(productive_grammar)
    for index, found in enumerate(reachable_history):
        steps.append(f"R{subscript(index)} = {format_set(found, order)}")
    reachable = reachable_history[-1]

    result = Grammar(grammar.start)
    dropped = []
    for lhs, rhs in productive_grammar.all_rules():
        if lhs in reachable:
            result.add_rule(lhs, rhs)
        else:
            dropped.append(format_rule(lhs, rhs))
    unreachable = [nt for nt in order if nt in productive and nt not in reachable]
    if unreachable:
        steps.append(
            f"Недосяжні нетермінали: {', '.join(unreachable)}. "
            f"Видаляємо їх та їхні правила: {'; '.join(dropped)}."
        )
    else:
        steps.append("Недосяжних нетерміналів немає.")

    if not unproductive and not unreachable:
        steps.append("Граматика не містить несуттєвих символів і залишається без змін.")
    return Outcome(result, steps)
