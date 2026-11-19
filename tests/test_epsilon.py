from helpers import parse, rule_set

from sipl.formal import (
    has_epsilon_rules,
    language_up_to,
    remove_epsilon_rules,
    remove_useless,
)


def test_book_example_matches_textbook_result():
    grammar = parse("S → AbCa|ABB|BScB|aSB, A → Aa|ε, B → bB|ε, C → Cc|c")
    outcome = remove_epsilon_rules(grammar)
    expected = parse(
        "S → AbCa|ABB|BScB|aSB|bCa|BB|AB|A|BSc|ScB|Sc|aS|B|BcB|aB|Bc|cB|c|a, "
        "A → Aa|a, B → bB|b, C → Cc|c"
    )
    assert rule_set(outcome.grammar) == rule_set(expected)
    assert outcome.empty_word is True


def test_variant1():
    grammar = parse("S → bBA|DcBA|DAAC|AcC, A → ε|bAc, B → ε|bB, C → ε|cC, D → d|dD")
    outcome = remove_epsilon_rules(grammar)
    assert not has_epsilon_rules(outcome.grammar)
    assert outcome.empty_word is False
    assert set(outcome.grammar.alternatives("S")) == {
        tuple(w) for w in
        ["bBA", "bB", "bA", "b", "DcBA", "DcB", "DcA", "Dc", "DAAC", "DAA", "DAC", "DC", "DA", "D", "AcC", "cC", "Ac", "c"]
    }
    assert outcome.grammar.alternatives("A") == [tuple("bAc"), tuple("bc")]


def test_language_loses_only_empty_word():
    grammar = parse("S → AB\nA → aA | ε\nB → bB | ε")
    outcome = remove_epsilon_rules(grammar)
    assert language_up_to(outcome.grammar, 6) == language_up_to(grammar, 6) - {""}
    assert outcome.empty_word is True


def test_grammar_without_epsilon_is_unchanged():
    grammar = parse("S → aSb | ab")
    outcome = remove_epsilon_rules(grammar)
    assert rule_set(outcome.grammar) == rule_set(grammar)
    assert outcome.empty_word is False


def test_trivial_self_rules_are_not_added():
    outcome = remove_epsilon_rules(parse("S → AS | a\nA → ε | b"))
    assert ("S", ("S",)) not in rule_set(outcome.grammar)


def test_nullable_only_through_other_symbols():
    grammar = parse("S → AB | c\nA → B\nB → ε")
    outcome = remove_epsilon_rules(grammar)
    cleaned = remove_useless(outcome.grammar).grammar
    assert language_up_to(cleaned, 3) == {"c"}
    assert outcome.empty_word is True
