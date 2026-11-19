import json
import random

import pytest

from sipl.cli import main
from sipl.formal import (
    EquationSyntaxError,
    EquationSystem,
    Family,
    Grammar,
    approximate,
    compare_with_grammar,
    language_up_to,
)
from sipl.formal.equations import explain, format_words

PR5 = "S = {aaa}A\nA = {dd}A{c} ∪ {ε}"


# ---------- розбір та форматування ----------


def test_parse_pr5_system():
    system = EquationSystem.from_text(PR5)
    assert system.start == "S"
    assert system.equations["S"] == [("a", "a", "a", "A")]
    assert system.equations["A"] == [("d", "d", "A", "c"), ()]


def test_roundtrip_text():
    system = EquationSystem.from_text(PR5)
    assert str(system) == PR5
    assert str(EquationSystem.from_text(str(system))) == PR5


def test_comma_and_pipe_separators_as_in_the_workbook():
    system = EquationSystem.from_text("S = {aaa}A, A = {dd}A{c} | {ε}")
    assert str(system) == PR5


def test_empty_set_summand_is_dropped():
    system = EquationSystem.from_text("S = {a}S ∪ ∅ ∪ {b}\nT = ∅\n")
    assert system.equations["S"] == [("a", "S"), ("b",)]
    assert system.equations["T"] == []
    assert approximate(system, 3).limit["T"] == frozenset()


def test_bare_terminals_and_primes():
    system = EquationSystem.from_text("S = aB′\nB′ = b ∪ {ε}")
    assert system.equations["S"] == [("a", "B′")]


@pytest.mark.parametrize(
    "text, fragment",
    [
        ("S {a}", "немає «=»"),
        ("S = {a", "закривної дужки"),
        ("S = {}", "порожні дужки"),
        ("S = {aT}", "лише термінали"),
        ("S = {a}T", "немає рівнянь для змінних: T"),
        ("ab = {a}", "одна змінна"),
        ("S = {a} ∪ ", "порожній доданок"),
        ("S =", "порожній доданок"),
        ("S = {a} ? S", "неочікуваний символ"),
    ],
)
def test_syntax_errors_are_explained(text, fragment):
    with pytest.raises(EquationSyntaxError) as info:
        EquationSystem.from_text(text)
    assert fragment in str(info.value)


def test_grammar_conversion_both_ways():
    grammar = Grammar.from_text("S → aaaA\nA → ddAc | ε")
    system = EquationSystem.from_grammar(grammar)
    assert str(system) == PR5
    assert set(system.to_grammar().all_rules()) == set(grammar.all_rules())


def test_nonterminal_without_rules_becomes_empty_set():
    system = EquationSystem.from_grammar(Grammar.from_text("S → aT | b"))
    assert system.equations["T"] == []
    assert approximate(system, 4).limit["S"] == {"b"}


# ---------- наближення: ваші формули з ПР5 як еталон ----------


def test_pr5_approximations_match_hand_computation():
    result = approximate(EquationSystem.from_text(PR5), 40)
    for k in range(1, 7):
        assert result.levels[k]["A"] == {"d" * (2 * i) + "c" * i for i in range(k)}
        assert result.levels[k]["S"] == {"aaa" + "d" * (2 * i) + "c" * i for i in range(k - 1)}
    assert result.levels[0] == {"S": frozenset(), "A": frozenset()}


def test_approximations_are_monotone():
    for text in (PR5, "S = {a}S{b}S ∪ {ε}", "S = {a}T\nT = {b}S ∪ {b}"):
        result = approximate(EquationSystem.from_text(text), 9)
        for before, after in zip(result.levels, result.levels[1:]):
            assert all(before[v] <= after[v] for v in before)


def test_fixed_point_is_really_fixed():
    from sipl.formal.equations import step

    for text in (PR5, "S = {a}S{b}S ∪ {ε}", "S = {a}T\nT = {b}S ∪ {b}"):
        system = EquationSystem.from_text(text)
        result = approximate(system, 8)
        assert result.stable_at is not None
        assert step(system, result.limit, 8) == result.limit


def test_stable_at_for_pr5():
    result = approximate(EquationSystem.from_text(PR5), 12)
    assert result.stable_at == 5
    assert len(result.levels) == 6


def test_zero_length_limit():
    result = approximate(EquationSystem.from_text(PR5), 0)
    assert result.limit["S"] == frozenset()
    assert result.limit["A"] == {""}


def test_entry_levels():
    result = approximate(EquationSystem.from_text(PR5), 12)
    assert result.entry_levels("S") == {
        "aaa": 2,
        "aaaddc": 3,
        "aaaddddcc": 4,
        "aaaddddddccc": 5,
    }


def test_mutual_recursion():
    result = approximate(EquationSystem.from_text("S = {a}T\nT = {b}S ∪ {b}"), 6)
    assert result.limit["S"] == {"ab", "abab", "ababab"}
    assert result.limit["T"] == {"b", "bab", "babab"}


def test_balanced_parentheses_counts():
    result = approximate(EquationSystem.from_text("S = {a}S{b}S ∪ {ε}"), 10)
    # числа Каталана: 1, 1, 2, 5, 14, 42 для довжин 0, 2, 4, …, 10
    by_length = {}
    for word in result.limit["S"]:
        by_length[len(word)] = by_length.get(len(word), 0) + 1
    assert [by_length[n] for n in range(0, 11, 2)] == [1, 1, 2, 5, 14, 42]


def test_explain_shows_substitution():
    result = approximate(EquationSystem.from_text(PR5), 12)
    text = "\n".join(explain(result, 2))
    assert "A₂ = {dd}A₁{c} ∪ {ε} = {ε, ddc}" in text
    assert "S₁ = {aaa}A₀ = ∅" in text
    assert "Крок 3" not in text


def test_format_words_truncates():
    assert format_words({"", "a", "b", "c"}, 2) == "{ε, a, … (+2)}"
    assert format_words(set()) == "∅"


# ---------- порівняння з граматикою ----------


def test_comparison_equal_for_pr5():
    result = approximate(EquationSystem.from_text(PR5), 14)
    grammar = Grammar.from_text("S → aaaA\nA → ddAc | ε")
    assert all(c.equal for c in compare_with_grammar(result, grammar))


def test_comparison_reports_difference():
    result = approximate(EquationSystem.from_text(PR5), 10)
    wrong = Grammar.from_text("S → aaaA\nA → dAc | ε")
    (s, a) = compare_with_grammar(result, wrong)
    assert not s.equal and "aaadc" in s.only_in_grammar
    assert "aaaddc" in s.only_in_equations


# ---------- конструктор родини: незалежний еталон ----------


def test_family_pr5_values():
    family = Family("aaa", "dd", "", "c", "")
    assert family.describe() == "L = { aaa(dd)ⁿcⁿ | n ≥ 0 }"
    assert str(family.equations()) == PR5
    assert family.words(12) == {"aaa", "aaaddc", "aaaddddcc", "aaaddddddccc"}


@pytest.mark.parametrize("seed", range(40))
def test_random_families_equations_grammar_and_direct_enumeration_agree(seed):
    rnd = random.Random(seed)

    def word(max_len):
        return "".join(rnd.choice("abc") for _ in range(rnd.randint(0, max_len)))

    left, right = word(3), word(3)
    if not left and not right:
        left = "a"
    family = Family(word(3), left, word(2), right, word(3))
    max_length = 12
    target = family.words(max_length)
    system = family.equations()
    assert set(approximate(system, max_length).limit["S"]) == target
    assert language_up_to(family.grammar(), max_length) == target


def test_family_rejects_bad_input():
    with pytest.raises(EquationSyntaxError):
        Family("a", "", "", "", "b")
    with pytest.raises(EquationSyntaxError):
        Family("A", "a", "", "b", "")


# ---------- CLI ----------


def test_cli_solve_text(examples_dir, capsys):
    code = main(["eq", "solve", str(examples_dir.parent / "equations" / "pr5_variant15.txt"),
                 "--max-length", "12", "--steps", "3", "--compare", str(examples_dir / "pr5_variant15.txt")])
    out = capsys.readouterr().out
    assert code == 0
    assert "S₃ = {aaa}A₂ = {aaa, aaaddc}" in out
    assert "S: R(E) = L(G) ✓" in out


def test_cli_solve_accepts_grammar_file(examples_dir, capsys):
    assert main(["eq", "solve", str(examples_dir / "pr5_variant15.txt"), "--max-length", "8"]) == 0
    assert "A = {dd}A{c} ∪ {ε}" in capsys.readouterr().out


def test_cli_solve_json(examples_dir, capsys):
    code = main(["eq", "solve", str(examples_dir.parent / "equations" / "pr5_variant15.txt"),
                 "--max-length", "8", "--format", "json"])
    data = json.loads(capsys.readouterr().out)
    assert code == 0
    assert data["solution"]["S"] == ["aaa", "aaaddc"]
    assert data["levels"][0] == {"S": [], "A": []}
    assert data["stable_at"] == 3
    assert data["entry_levels"]["aaaddc"] == 3


def test_cli_mismatch_gives_exit_code_3(examples_dir, tmp_path, capsys):
    other = tmp_path / "other.txt"
    other.write_text("S → aaaA\nA → dAc | ε", encoding="utf-8")
    code = main(["eq", "solve", str(examples_dir.parent / "equations" / "pr5_variant15.txt"),
                 "--max-length", "10", "--compare", str(other)])
    assert code == 3
    assert "НЕ збігається" in capsys.readouterr().out


def test_cli_convert_both_directions(examples_dir, capsys):
    assert main(["eq", "convert", str(examples_dir / "pr5_variant15.txt")]) == 0
    assert "A = {dd}A{c} ∪ {ε}" in capsys.readouterr().out
    assert main(["eq", "convert", str(examples_dir.parent / "equations" / "pr5_variant15.txt")]) == 0
    assert "A → ddAc | ε" in capsys.readouterr().out


def test_cli_build(capsys):
    code = main(["eq", "build", "--prefix", "aaa", "--left", "dd", "--right", "c"])
    out = capsys.readouterr().out
    assert code == 0
    assert "P2: A → ddAc" in out and "R(E) = L: так" in out and "L(G) = L: так" in out


def test_cli_build_rejects_degenerate_family(capsys):
    assert main(["eq", "build", "--prefix", "a"]) == 1
    assert "не можуть бути одночасно порожніми" in capsys.readouterr().err


def test_cli_errors(tmp_path, capsys):
    assert main(["eq", "solve", "nope.txt"]) == 2
    bad = tmp_path / "bad.txt"
    bad.write_text("S = {a}T", encoding="utf-8")
    assert main(["eq", "solve", str(bad)]) == 1
    assert "Помилка у системі рівнянь" in capsys.readouterr().err
