from __future__ import annotations

import string
from collections.abc import Callable

from sipl.formal.cleanup import remove_useless
from sipl.formal.epsilon import remove_epsilon_rules
from sipl.formal.grammar import PRIME, Grammar, Rule, format_rule, is_nonterminal
from sipl.formal.outcome import Outcome


def fresh_name(used: set[str]) -> str:
    for letter in string.ascii_uppercase:
        if letter not in used:
            return letter
    index = 1
    while f"N{index}" in used:
        index += 1
    return f"N{index}"


def _wrapper_name(terminal: str, used: set[str]) -> str:
    base = terminal.upper() if terminal[0].isalpha() else "T"
    candidate = base + PRIME
    while candidate in used:
        candidate += PRIME
    return candidate


def replace_terminals(grammar: Grammar) -> Outcome:
    used = set(grammar.nonterminals())
    wrappers: dict[str, str] = {}
    result = Grammar(grammar.start)
    changed = []
    for lhs, rhs in grammar.all_rules():
        if len(rhs) < 2:
            result.add_rule(lhs, rhs)
            continue
        new_rhs = []
        for symbol in rhs:
            if is_nonterminal(symbol):
                new_rhs.append(symbol)
                continue
            if symbol not in wrappers:
                wrappers[symbol] = _wrapper_name(symbol, used)
                used.add(wrappers[symbol])
            new_rhs.append(wrappers[symbol])
        new_rhs = tuple(new_rhs)
        result.add_rule(lhs, new_rhs)
        if new_rhs != rhs:
            changed.append(f"{format_rule(lhs, rhs)} на {format_rule(lhs, new_rhs)}")
    for terminal, name in wrappers.items():
        result.add_rule(name, (terminal,))

    if not wrappers:
        return Outcome(result, ["У правилах довжини більше одного символу терміналів немає."])
    created = "; ".join(format_rule(name, (terminal,)) for terminal, name in wrappers.items())
    steps = [f"Вводимо нові нетермінали: {created}.", "Замінюємо правила: " + "; ".join(changed) + "."]
    return Outcome(result, steps)


def _is_unit(rhs: Rule) -> bool:
    return len(rhs) == 1 and is_nonterminal(rhs[0])


def _unit_targets(grammar: Grammar, symbol: str) -> list[str]:
    seen = {symbol}
    found: list[str] = []
    queue = [symbol]
    while queue:
        current = queue.pop(0)
        for rhs in grammar.alternatives(current):
            if _is_unit(rhs) and rhs[0] not in seen:
                seen.add(rhs[0])
                found.append(rhs[0])
                queue.append(rhs[0])
    return found


def remove_unit_rules(grammar: Grammar) -> Outcome:
    result = Grammar(grammar.start)
    for lhs, rhs in grammar.all_rules():
        if not _is_unit(rhs):
            result.add_rule(lhs, rhs)

    steps = []
    for lhs in grammar.nonterminals():
        targets = _unit_targets(grammar, lhs)
        if not targets:
            continue
        added = []
        for target in targets:
            for rhs in grammar.alternatives(target):
                if not _is_unit(rhs) and result.add_rule(lhs, rhs):
                    added.append(format_rule(lhs, rhs))
        direct = ", ".join(format_rule(lhs, rhs) for rhs in grammar.alternatives(lhs) if _is_unit(rhs))
        line = f"Видаляємо {direct}; " if direct else f"Для {lhs} через ланцюжок одиничних правил; "
        line += "додаємо правила " + "; ".join(added) if added else "усі потрібні правила вже є"
        steps.append(line + ".")
    if not steps:
        steps.append("Одиничних правил немає.")
    return Outcome(result, steps)


def split_long_rules(grammar: Grammar) -> Outcome:
    used = set(grammar.nonterminals())
    names: dict[Rule, str] = {}
    helpers: list[tuple[str, Rule]] = []

    def name_for(suffix: Rule) -> str:
        if suffix in names:
            return names[suffix]
        name = fresh_name(used)
        used.add(name)
        names[suffix] = name
        slot = len(helpers)
        helpers.append((name, ()))
        body = suffix if len(suffix) == 2 else (suffix[0], name_for(suffix[1:]))
        helpers[slot] = (name, body)
        return name

    result = Grammar(grammar.start)
    steps = []
    for lhs, rhs in grammar.all_rules():
        if len(rhs) <= 2:
            result.add_rule(lhs, rhs)
            continue
        before = len(helpers)
        main = (rhs[0], name_for(rhs[1:]))
        result.add_rule(lhs, main)
        created = [format_rule(name, body) for name, body in helpers[before:]]
        line = f"{format_rule(lhs, rhs)} замінюємо на {format_rule(lhs, main)}"
        line += "; нові правила: " + "; ".join(created) if created else " (потрібні правила вже додано)"
        steps.append(line + ".")
    for name, body in helpers:
        result.add_rule(name, body)
    if not steps:
        steps.append("Правил із трьома й більше нетерміналами немає.")
    return Outcome(result, steps)


def add_empty_word_start(grammar: Grammar) -> Outcome:
    used = set(grammar.nonterminals())
    new_start = grammar.start + PRIME
    while new_start in used:
        new_start += PRIME
    result = Grammar(new_start)
    result.add_rule(new_start, ())
    for rhs in grammar.alternatives(grammar.start):
        result.add_rule(new_start, rhs)
    for lhs, rhs in grammar.all_rules():
        result.add_rule(lhs, rhs)
    steps = [
        f"ε ∈ L(G), тому вводимо нову аксіому {new_start} з правилом {format_rule(new_start, ())} "
        f"та копіями всіх правил для {grammar.start}."
    ]
    return Outcome(result, steps)


def _run(
    steps: list[str],
    title: str,
    transform: Callable[[Grammar], Outcome],
    grammar: Grammar,
    quiet_if_unchanged: bool = False,
) -> Outcome:
    outcome = transform(grammar)
    if quiet_if_unchanged and str(outcome.grammar) == str(grammar):
        return outcome
    steps.append(f"-- {title}")
    steps.extend(outcome.steps)
    return outcome


def to_chomsky(grammar: Grammar) -> Outcome:
    steps: list[str] = []
    current = _run(steps, "Видалення несуттєвих символів", remove_useless, grammar).grammar
    epsilon = _run(steps, "Видалення ε-правил", remove_epsilon_rules, current)
    current = _run(steps, "Видалення несуттєвих символів після ε-правил", remove_useless, epsilon.grammar, True).grammar
    current = _run(steps, "Заміна терміналів", replace_terminals, current).grammar
    current = _run(steps, "Видалення одиничних правил", remove_unit_rules, current).grammar
    current = _run(steps, "Видалення несуттєвих символів після одиничних правил", remove_useless, current, True).grammar
    current = _run(steps, "Розбиття довгих правил", split_long_rules, current).grammar
    if epsilon.empty_word:
        current = _run(steps, "Порожнє слово", add_empty_word_start, current).grammar
    return Outcome(current, steps, epsilon.empty_word)
