import random

import pytest
from helpers import parse

from sipl.formal import (
    Grammar,
    has_unit_rules,
    is_chomsky,
    language_up_to,
    remove_epsilon_rules,
    remove_useless,
    to_chomsky,
)


def assert_chomsky_equivalent(grammar: Grammar, max_length: int) -> None:
    outcome = to_chomsky(grammar)
    assert is_chomsky(outcome.grammar)
    assert language_up_to(outcome.grammar, max_length) == language_up_to(grammar, max_length)
    assert all(isinstance(step, str) and step for step in outcome.steps)


def test_variant1_from_practice_4(examples_dir):
    grammar = Grammar.from_text((examples_dir / "pr4_variant1.txt").read_text(encoding="utf-8"))
    assert_chomsky_equivalent(grammar, 8)


def test_book_example(examples_dir):
    grammar = Grammar.from_text((examples_dir / "pr4_book_example.txt").read_text(encoding="utf-8"))
    assert_chomsky_equivalent(grammar, 6)


def test_book_task(examples_dir):
    grammar = Grammar.from_text((examples_dir / "pr4_book_task.txt").read_text(encoding="utf-8"))
    assert_chomsky_equivalent(grammar, 7)


def test_terminal_wrappers_follow_book_naming():
    outcome = to_chomsky(parse("S → aSb | ab"))
    assert ("A′" in outcome.grammar.rules) and ("B′" in outcome.grammar.rules)


def test_long_rules_are_split_into_pairs():
    outcome = to_chomsky(parse("S → ABCDE\nA → a\nB → b\nC → c\nD → d\nE → e"))
    assert all(len(rhs) <= 2 for _, rhs in outcome.grammar.all_rules())
    assert language_up_to(outcome.grammar, 6) == {"abcde"}


def test_unit_rule_chain_and_cycle():
    grammar = parse("S → A | a\nA → B\nB → A | b")
    outcome = to_chomsky(grammar)
    assert is_chomsky(outcome.grammar)
    assert not has_unit_rules(outcome.grammar)
    assert language_up_to(outcome.grammar, 3) == {"a", "b"}


def test_empty_word_gets_new_start_symbol():
    grammar = parse("S → aS | ε")
    outcome = to_chomsky(grammar)
    assert outcome.empty_word is True
    assert outcome.grammar.start == "S′"
    assert is_chomsky(outcome.grammar)
    assert language_up_to(outcome.grammar, 4) == {"", "a", "aa", "aaa", "aaaa"}


def test_language_with_only_empty_word():
    outcome = to_chomsky(parse("S → ε"))
    assert is_chomsky(outcome.grammar)
    assert language_up_to(outcome.grammar, 3) == {""}


def test_empty_language():
    outcome = to_chomsky(parse("S → Sa"))
    assert outcome.grammar.rules == {}
    assert language_up_to(outcome.grammar, 3) == set()


def random_grammar(rng: random.Random) -> Grammar:
    symbols = ["S", "A", "B", "a", "b"]
    rules = {}
    for nonterminal in ["S", "A", "B"]:
        alternatives = {
            tuple(rng.choice(symbols) for _ in range(rng.randint(0, 3)))
            for _ in range(rng.randint(1, 3))
        }
        rules[nonterminal] = sorted(alternatives)
    return Grammar("S", rules)


@pytest.mark.parametrize("seed", range(150))
def test_random_grammars_keep_their_language(seed):
    grammar = random_grammar(random.Random(seed))
    useless = remove_useless(grammar).grammar
    assert language_up_to(useless, 5) == language_up_to(grammar, 5)
    epsilon = remove_epsilon_rules(grammar).grammar
    assert language_up_to(epsilon, 5) == language_up_to(grammar, 5) - {""}
    assert_chomsky_equivalent(grammar, 5)
