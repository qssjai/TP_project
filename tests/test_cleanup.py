from helpers import parse, rule_set

from sipl.formal import language_up_to, remove_useless


def test_book_example_removes_unproductive_d():
    grammar = parse("S → AbCa|ABB|BScB|aSB, A → Aa|ε, B → bB|ε, C → Dc|Cc|c, D → Dd")
    outcome = remove_useless(grammar)
    expected = parse("S → AbCa|ABB|BScB|aSB, A → Aa|ε, B → bB|ε, C → Cc|c")
    assert rule_set(outcome.grammar) == rule_set(expected)
    assert any("D" in step and "Непродуктивні" in step for step in outcome.steps)


def test_variant1_has_no_useless_symbols():
    grammar = parse("S → bBA|DcBA|DAAC|AcC, A → ε|bAc, B → ε|bB, C → ε|cC, D → d|dD")
    outcome = remove_useless(grammar)
    assert rule_set(outcome.grammar) == rule_set(grammar)
    assert outcome.steps[-1].startswith("Граматика не містить")


def test_unreachable_nonterminal_is_removed():
    outcome = remove_useless(parse("S → aA\nA → a\nB → b"))
    assert "B" not in outcome.grammar.rules
    assert any("Недосяжні нетермінали: B" in step for step in outcome.steps)


def test_nonterminal_reachable_only_through_unproductive_one_is_removed():
    outcome = remove_useless(parse("S → a | AB\nA → A\nB → b"))
    assert rule_set(outcome.grammar) == {("S", ("a",))}


def test_unproductive_start_gives_empty_language():
    outcome = remove_useless(parse("S → Sa"))
    assert outcome.grammar.rules == {}
    assert language_up_to(outcome.grammar, 5) == set()


def test_language_is_preserved():
    grammar = parse("S → aSb | A | ab\nA → B\nB → c\nC → d")
    outcome = remove_useless(grammar)
    assert language_up_to(outcome.grammar, 6) == language_up_to(grammar, 6)
