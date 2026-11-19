import json

import pytest

from sipl.cli import main
from sipl.formal import Grammar
from sipl.formal.pumping import (
    NAMED_LANGUAGES,
    Decomposition,
    check,
    decompositions,
    explore,
    expression_member,
    grammar_member,
    word_from_expression,
)

PR6_WORD = "'a'*(3*k)+'b'+'d'*(2*k)+'c'*k"


def test_decompositions_respect_lemma_conditions():
    word, k = "aabb", 3
    found = list(decompositions(word, k))
    assert found
    for d in found:
        assert d.word == word
        assert len(d.t1 + d.t2) >= 1
        assert len(d.t1 + d.x + d.t2) <= k
    assert len(found) == len(set(found))


def test_decomposition_count_matches_brute_force():
    word, k = "abcab", 3
    n = len(word)
    expected = 0
    for a in range(n + 1):
        for b in range(a, n + 1):
            for c in range(b, n + 1):
                for d in range(c, n + 1):
                    if (b - a) + (d - c) >= 1 and d - a <= k:
                        expected += 1
    assert len(list(decompositions(word, k))) == expected


def test_pump_and_marked():
    d = Decomposition("a", "b", "c", "b", "d")
    assert d.pump(0) == "acd" and d.pump(2) == "abbcbbd"
    assert d.marked() == "a | b | c | b | d"


def test_anbn_has_pumpable_decomposition():
    member = NAMED_LANGUAGES["anbn"][1]
    e = explore("aabb", 3, member)
    assert e.in_language and e.good and not e.witness
    assert Decomposition("", "a", "a", "b", "b") in [v.decomposition for v in e.good]


@pytest.mark.parametrize("k", [1, 2, 3, 4])
def test_pr6_word_is_a_witness_for_each_k(k):
    """Обчислювальна ілюстрація доведення з ПР6: жоден розклад не накачується."""
    word = word_from_expression(PR6_WORD, k)
    e = explore(word, k, NAMED_LANGUAGES["pr6"][1])
    assert e.in_language and e.witness and not e.good


def test_anbncn_witness():
    e = explore("aabbcc", 2, NAMED_LANGUAGES["anbncn"][1])
    assert e.witness


def test_regular_language_always_pumps():
    member = expression_member("set(w) <= {'a'}")
    assert explore("aaaa", 2, member).good


def test_word_not_in_language_is_not_a_witness():
    e = explore("abab", 2, NAMED_LANGUAGES["anbn"][1])
    assert not e.in_language and not e.witness


def test_check_reports_first_failing_i():
    member = NAMED_LANGUAGES["anbn"][1]
    v = check(Decomposition("", "", "", "a", "abb"), member)
    assert v.failed_i == 0 and not v.pumps
    assert v.to_dict()["pumped_word"] == "abb"


def test_grammar_member_matches_language_up_to():
    from sipl.formal import language_up_to

    for text in ("S → aSb | ε", "S → SS | aSb | ab", "S → AB\nA → aA | a\nB → bB | ε"):
        g = Grammar.from_text(text)
        member = grammar_member(g)
        words = language_up_to(g, 6)
        for n in range(7):
            for i in range(2**n):
                w = "".join("ab"[(i >> j) & 1] for j in range(n))
                assert member(w) == (w in words), (text, w)


def test_expression_is_sandboxed():
    member = expression_member("__import__('os')")
    with pytest.raises(NameError):
        member("a")


def test_cli_text_has_disclaimer_and_witness(capsys):
    code = main(["pump", "--lang", "pr6", "--word-expr", PR6_WORD, "-k", "2"])
    out = capsys.readouterr().out
    assert code == 0
    assert "навчальний асистент" in out
    assert "накачуються: 0" in out
    assert "жоден розклад не накачується" in out


def test_cli_grammar_and_json(examples_dir, capsys):
    code = main(["pump", "--grammar", str(examples_dir / "anbn.txt"), "--word", "aabb", "-k", "3", "--format", "json"])
    data = json.loads(capsys.readouterr().out)
    assert code == 0
    assert "disclaimer" in data
    assert data["results"][0]["witness"] is False
    assert data["results"][0]["pumps"]


def test_cli_single_split(capsys):
    args = ["pump", "--lang", "anbn", "--word", "aabb", "-k", "3", "--split"]
    assert main([*args, "|a|a|b|b"]) == 0
    assert "накачуються: 1" in capsys.readouterr().out
    assert main([*args, "a|b|a|b|b"]) == 1  # інше слово
    assert "розклад дає слово" in capsys.readouterr().err
    assert main([*args, "|aabb|||"]) == 1  # |t1xt2| > k
    assert "порушує" in capsys.readouterr().err


def test_cli_errors(capsys):
    assert main(["pump", "--grammar", "no.txt", "--word", "a", "-k", "1"]) == 2
    assert main(["pump", "--pred", "w ==", "--word", "a", "-k", "1"]) == 1
    assert main(["pump", "--lang", "anbn", "--word-expr", "1+1", "-k", "1"]) == 1


def test_expression_can_use_lambda_and_comprehensions():
    member = expression_member("(lambda n: w == 'a' * n + 'b' * n)(w.count('a'))")
    assert member("aabb") and not member("aab")
    assert word_from_expression("''.join('ab' for _ in range(k))", 3) == "ababab"
