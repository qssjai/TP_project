from sipl.formal import Grammar


def rule_set(grammar: Grammar) -> set[tuple[str, tuple[str, ...]]]:
    return set(grammar.all_rules())


def parse(text: str) -> Grammar:
    return Grammar.from_text(text)
