import pytest

from sipl.formal import Grammar, GrammarSyntaxError


def test_parses_compact_book_notation():
    grammar = Grammar.from_text("S → AbCa|ABB|BScB|aSB, A → Aa|ε")
    assert grammar.start == "S"
    assert grammar.alternatives("S")[0] == ("A", "b", "C", "a")
    assert grammar.alternatives("A") == [("A", "a"), ()]


def test_parses_ascii_arrow_and_multiple_lines():
    grammar = Grammar.from_text("S -> a S b | eps\nS -> c")
    assert grammar.alternatives("S") == [("a", "S", "b"), (), ("c",)]


def test_prime_belongs_to_previous_symbol():
    grammar = Grammar.from_text("S → B′C′ | A'")
    assert grammar.alternatives("S") == [("B′", "C′"), ("A′",)]


def test_symbols_separated_by_spaces_may_be_long():
    grammar = Grammar.from_text("E → E plus Term | Term")
    assert grammar.alternatives("E")[0] == ("E", "plus", "Term")


def test_nonterminals_and_terminals():
    grammar = Grammar.from_text("S → aAb\nA → c")
    assert grammar.nonterminals() == ["S", "A"]
    assert grammar.terminals() == ["a", "b", "c"]


def test_str_round_trip():
    text = "S → aSb | ε\nA → c"
    assert str(Grammar.from_text(text)) == text


def test_comments_are_ignored():
    grammar = Grammar.from_text("S → a  # коментар\n# порожній рядок\nS → b")
    assert grammar.alternatives("S") == [("a",), ("b",)]


@pytest.mark.parametrize(
    "text",
    ["", "S a b", "a → b", "S → a |", "S → ′a", "AB → a"],
)
def test_invalid_grammars_raise_syntax_error(text):
    with pytest.raises(GrammarSyntaxError):
        Grammar.from_text(text)
