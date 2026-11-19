from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, field

from sipl.formal.grammar import (
    EPSILON,
    Grammar,
    Rule,
    format_rule,
    is_nonterminal,
    join_symbols,
)

Step = tuple[Rule, "tuple[str, Rule] | None"]


@dataclass
class Tree:
    symbol: str
    children: list[Tree] = field(default_factory=list)

    @property
    def is_terminal(self) -> bool:
        return not is_nonterminal(self.symbol)

    def rule(self) -> tuple[str, Rule]:
        return self.symbol, tuple(child.symbol for child in self.children)

    def leaves(self) -> Rule:
        if self.is_terminal:
            return (self.symbol,)
        return tuple(leaf for child in self.children for leaf in child.leaves())

    def height(self) -> int:
        if self.is_terminal:
            return 0
        return 1 + max((child.height() for child in self.children), default=0)

    def to_dict(self) -> dict:
        return {"symbol": self.symbol, "children": [child.to_dict() for child in self.children]}

    def to_text(self) -> str:
        lines = [self.symbol]
        self._add_text(lines, "")
        return "\n".join(lines)

    def _add_text(self, lines: list[str], prefix: str) -> None:
        if not self.is_terminal and not self.children:
            lines.append(f"{prefix}└── {EPSILON}")
            return
        for index, child in enumerate(self.children):
            last = index == len(self.children) - 1
            lines.append(f"{prefix}{'└── ' if last else '├── '}{child.symbol}")
            child._add_text(lines, prefix + ("    " if last else "│   "))


def find_trees(grammar: Grammar, word: Rule, max_depth: int = 10, limit: int = 100) -> list[Tree]:
    memo: dict[tuple[str, int, int, int], list[Tree]] = {}

    def derive(symbol: str, start: int, end: int, depth: int) -> list[Tree]:
        if not is_nonterminal(symbol):
            return [Tree(symbol)] if end - start == 1 and word[start] == symbol else []
        if depth == 0:
            return []
        key = (symbol, start, end, depth)
        if key in memo:
            return memo[key]
        found: list[Tree] = []
        for rhs in grammar.alternatives(symbol):
            for children in split(rhs, 0, start, end, depth - 1):
                found.append(Tree(symbol, children))
                if len(found) >= limit:
                    break
            if len(found) >= limit:
                break
        memo[key] = found
        return found

    def split(rhs: Rule, position: int, start: int, end: int, depth: int) -> Iterator[list[Tree]]:
        if position == len(rhs):
            if start == end:
                yield []
            return
        cuts = [end] if position == len(rhs) - 1 else range(start, end + 1)
        for cut in cuts:
            for tree in derive(rhs[position], start, cut, depth):
                for rest in split(rhs, position + 1, cut, end, depth):
                    yield [tree] + rest

    return derive(grammar.start, 0, len(word), max_depth)


def is_ambiguous(grammar: Grammar, word: Rule, max_depth: int = 10) -> bool:
    return len(find_trees(grammar, word, max_depth, limit=2)) >= 2


def _rule_order(tree: Tree, leftmost: bool) -> Iterator[tuple[str, Rule]]:
    if tree.is_terminal:
        return
    yield tree.rule()
    children = tree.children if leftmost else list(reversed(tree.children))
    for child in children:
        yield from _rule_order(child, leftmost)


def derivation_steps(tree: Tree, leftmost: bool = True) -> list[Step]:
    form: Rule = (tree.symbol,)
    steps: list[Step] = [(form, None)]
    for lhs, rhs in _rule_order(tree, leftmost):
        positions = [i for i, symbol in enumerate(form) if is_nonterminal(symbol)]
        index = positions[0] if leftmost else positions[-1]
        form = form[:index] + rhs + form[index + 1 :]
        steps.append((form, (lhs, rhs)))
    return steps


def format_derivation(steps: list[Step]) -> str:
    lines = []
    for form, rule in steps:
        text = join_symbols(form) or EPSILON
        lines.append(text if rule is None else f"⇒ {text}    [{format_rule(*rule)}]")
    return "\n".join(lines)


def steps_to_dicts(steps: list[Step]) -> list[dict]:
    return [
        {"form": join_symbols(form) or EPSILON, "rule": None if rule is None else format_rule(*rule)}
        for form, rule in steps
    ]


def trees_to_dot(trees: list[Tree]) -> str:
    lines = ["digraph derivation {", "  node [shape=plaintext];"]
    counter = 0

    def new_id() -> str:
        nonlocal counter
        counter += 1
        return f"n{counter}"

    def emit(node: Tree) -> str:
        ident = new_id()
        lines.append(f'    {ident} [label="{node.symbol}"];')
        if not node.is_terminal and not node.children:
            empty = new_id()
            lines.append(f'    {empty} [label="{EPSILON}"];')
            lines.append(f"    {ident} -> {empty};")
        for child in node.children:
            lines.append(f"    {ident} -> {emit(child)};")
        return ident

    for index, tree in enumerate(trees, start=1):
        lines.append(f"  subgraph cluster_{index} {{")
        lines.append(f'    label="Дерево {index}";')
        emit(tree)
        lines.append("  }")
    lines.append("}")
    return "\n".join(lines)
