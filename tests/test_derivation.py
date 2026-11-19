import json

from helpers import parse

from sipl.cli import main
from sipl.formal import (
    Grammar,
    Tree,
    derivation_steps,
    find_trees,
    format_derivation,
    is_ambiguous,
    trees_to_dot,
)


def load(examples_dir, name):
    return Grammar.from_text((examples_dir / name).read_text(encoding="utf-8"))


def test_tree_leaves_and_height():
    tree = Tree("S", [Tree("a"), Tree("S", [Tree("a"), Tree("b")]), Tree("b")])
    assert tree.leaves() == ("a", "a", "b", "b")
    assert tree.height() == 2


def test_empty_nonterminal_has_no_leaves():
    assert Tree("A").leaves() == ()


def test_single_tree_for_unambiguous_word(examples_dir):
    grammar = load(examples_dir, "anbn.txt")
    trees = find_trees(grammar, tuple("aabb"))
    assert len(trees) == 1
    assert trees[0].leaves() == tuple("aabb")
    assert not is_ambiguous(grammar, tuple("aabb"))


def test_word_outside_language_has_no_trees(examples_dir):
    grammar = load(examples_dir, "anbn.txt")
    assert find_trees(grammar, tuple("aab")) == []
    assert find_trees(grammar, ()) == []


def test_ambiguous_grammar_gives_two_trees(examples_dir):
    grammar = load(examples_dir, "ambiguous_ss.txt")
    trees = find_trees(grammar, tuple("aaa"))
    assert len(trees) == 2
    assert all(tree.leaves() == tuple("aaa") for tree in trees)
    assert is_ambiguous(grammar, tuple("aaa"))
    assert not is_ambiguous(grammar, tuple("aa"))


def test_empty_word_in_colloquium_grammar_has_two_trees(examples_dir):
    grammar = load(examples_dir, "colloquium_g.txt")
    trees = find_trees(grammar, ())
    assert len(trees) == 2
    assert {tree.children[0].symbol for tree in trees} == {"A", "C"}
    assert is_ambiguous(grammar, ())


def test_unit_cycle_is_cut_by_depth():
    grammar = parse("S → S | a")
    assert len(find_trees(grammar, ("a",), max_depth=5)) == 5


def test_limit_is_respected():
    grammar = parse("S → SS | a")
    assert len(find_trees(grammar, tuple("aaaaa"), limit=3)) == 3


def test_multi_symbol_terminals():
    grammar = parse("E → E plus E | x")
    trees = find_trees(grammar, ("x", "plus", "x", "plus", "x"))
    assert len(trees) == 2


def test_derivations_reach_the_word_and_use_the_tree_rules(examples_dir):
    grammar = load(examples_dir, "ambiguous_ss.txt")
    for tree in find_trees(grammar, tuple("aaaa")):
        for leftmost in (True, False):
            steps = derivation_steps(tree, leftmost)
            assert steps[0][0] == ("S",)
            assert steps[-1][0] == tuple("aaaa")
            used = [rule for _, rule in steps[1:]]
            for lhs, rhs in used:
                assert rhs in grammar.alternatives(lhs)
        left = sorted(rule for _, rule in derivation_steps(tree, True)[1:])
        right = sorted(rule for _, rule in derivation_steps(tree, False)[1:])
        assert left == right


def test_leftmost_and_rightmost_differ_in_order():
    grammar = parse("S → AB\nA → a\nB → b")
    tree = find_trees(grammar, tuple("ab"))[0]
    left = [form for form, _ in derivation_steps(tree, True)]
    right = [form for form, _ in derivation_steps(tree, False)]
    assert left == [("S",), ("A", "B"), ("a", "B"), ("a", "b")]
    assert right == [("S",), ("A", "B"), ("A", "b"), ("a", "b")]


def test_format_derivation_marks_epsilon():
    grammar = parse("S → A\nA → ε")
    tree = find_trees(grammar, ())[0]
    text = format_derivation(derivation_steps(tree))
    assert text.splitlines()[0] == "S"
    assert text.splitlines()[-1].startswith("⇒ ε")


def test_text_tree_shows_epsilon_leaf():
    tree = find_trees(parse("S → A\nA → ε"), ())[0]
    assert tree.to_text().splitlines() == ["S", "└── A", "    └── ε"]


def test_dot_contains_a_cluster_per_tree(examples_dir):
    grammar = load(examples_dir, "ambiguous_ss.txt")
    dot = trees_to_dot(find_trees(grammar, tuple("aaa")))
    assert dot.startswith("digraph")
    assert "cluster_1" in dot and "cluster_2" in dot


def test_cli_text_output(examples_dir, capsys):
    code = main(["derive", str(examples_dir / "anbn.txt"), "aabb"])
    output = capsys.readouterr().out
    assert code == 0
    assert "Знайдено дерев: 1" in output
    assert "Лівостороннє виведення" in output


def test_cli_reports_ambiguity(examples_dir, capsys):
    code = main(["derive", str(examples_dir / "ambiguous_ss.txt"), "aaa"])
    assert code == 0
    assert "неоднозначна" in capsys.readouterr().out


def test_cli_json_output_is_valid(examples_dir, capsys):
    main(["derive", str(examples_dir / "ambiguous_ss.txt"), "aaa", "--format", "json"])
    data = json.loads(capsys.readouterr().out)
    assert len(data) == 2
    assert data[0]["tree"]["symbol"] == "S"
    assert data[0]["leftmost"][0] == {"form": "S", "rule": None}


def test_cli_dot_output(examples_dir, capsys):
    main(["derive", str(examples_dir / "anbn.txt"), "ab", "--format", "dot"])
    assert capsys.readouterr().out.startswith("digraph")


def test_cli_word_with_nonterminal_is_an_error(examples_dir, capsys):
    assert main(["derive", str(examples_dir / "anbn.txt"), "aSb"]) == 1
    assert "лише з терміналів" in capsys.readouterr().err


def test_cli_word_not_in_language(examples_dir, capsys):
    code = main(["derive", str(examples_dir / "anbn.txt"), "aab"])
    assert code == 0
    assert "не знайдено" in capsys.readouterr().out
