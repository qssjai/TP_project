from __future__ import annotations

import re
from collections.abc import Iterator
from dataclasses import dataclass, field

EPSILON = "ε"
EMPTY_WORD_MARKS = {"ε", "eps", "epsilon"}
PRIME = "′"
ARROWS = ("→", "->")

Rule = tuple[str, ...]


class GrammarSyntaxError(ValueError):
    pass


def is_nonterminal(symbol: str) -> bool:
    return symbol[0].isupper()


def _is_short(symbol: str) -> bool:
    return len(symbol) == 1 or (len(symbol) == 2 and symbol[1] == PRIME)


def join_symbols(symbols: Rule) -> str:
    separator = "" if all(_is_short(s) for s in symbols) else " "
    return separator.join(symbols)


def format_rule(lhs: str, rhs: Rule) -> str:
    return f"{lhs} → {join_symbols(rhs) or EPSILON}"


def tokenize(text: str, line: int = 0) -> Rule:
    text = text.strip().replace("'", PRIME)
    if not text:
        raise GrammarSyntaxError(f"рядок {line}: порожній запис, для порожнього слова використайте ε")
    if text in EMPTY_WORD_MARKS:
        return ()
    if any(ch.isspace() for ch in text):
        return tuple(text.split())
    tokens: list[str] = []
    for ch in text:
        if ch == PRIME:
            if not tokens:
                raise GrammarSyntaxError(f"рядок {line}: штрих без символу в «{text}»")
            tokens[-1] += PRIME
        else:
            tokens.append(ch)
    return tuple(tokens)


def _parse_rule(part: str, line: int) -> tuple[str, list[Rule]]:
    for arrow in ARROWS:
        if arrow in part:
            left, right = part.split(arrow, 1)
            break
    else:
        raise GrammarSyntaxError(f"рядок {line}: немає стрілки → у правилі «{part}»")
    lhs = tokenize(left, line)
    if len(lhs) != 1 or not is_nonterminal(lhs[0]):
        raise GrammarSyntaxError(f"рядок {line}: ліва частина «{left.strip()}» має бути одним нетерміналом")
    alternatives = [tokenize(alt, line) for alt in right.split("|")]
    return lhs[0], alternatives


@dataclass
class Grammar:
    start: str
    rules: dict[str, list[Rule]] = field(default_factory=dict)

    @classmethod
    def from_text(cls, text: str, start: str | None = None) -> Grammar:
        grammar = cls(start or "")
        for number, line in enumerate(text.splitlines(), start=1):
            for part in re.split(r"[,;]", line.split("#", 1)[0]):
                if not part.strip():
                    continue
                lhs, alternatives = _parse_rule(part, number)
                if not grammar.start:
                    grammar.start = lhs
                for rhs in alternatives:
                    grammar.add_rule(lhs, rhs)
        if not grammar.rules:
            raise GrammarSyntaxError("граматика не містить жодного правила")
        if not is_nonterminal(grammar.start):
            raise GrammarSyntaxError(f"аксіома «{grammar.start}» має бути нетерміналом")
        return grammar

    def all_rules(self) -> Iterator[tuple[str, Rule]]:
        for lhs, alternatives in self.rules.items():
            for rhs in alternatives:
                yield lhs, rhs

    def alternatives(self, lhs: str) -> list[Rule]:
        return self.rules.get(lhs, [])

    def add_rule(self, lhs: str, rhs: Rule) -> bool:
        alternatives = self.rules.setdefault(lhs, [])
        if rhs in alternatives:
            return False
        alternatives.append(rhs)
        return True

    def remove_rule(self, lhs: str, rhs: Rule) -> None:
        alternatives = self.rules.get(lhs, [])
        if rhs in alternatives:
            alternatives.remove(rhs)
        if not alternatives:
            self.rules.pop(lhs, None)

    def copy(self) -> Grammar:
        return Grammar(self.start, {lhs: list(alts) for lhs, alts in self.rules.items()})

    def nonterminals(self) -> list[str]:
        ordered = [self.start]
        ordered.extend(lhs for lhs in self.rules if lhs != self.start)
        for _, rhs in self.all_rules():
            for symbol in rhs:
                if is_nonterminal(symbol) and symbol not in ordered:
                    ordered.append(symbol)
        return ordered

    def terminals(self) -> list[str]:
        found = {s for _, rhs in self.all_rules() for s in rhs if not is_nonterminal(s)}
        return sorted(found)

    def __str__(self) -> str:
        lines = []
        for lhs in self.nonterminals():
            if lhs in self.rules:
                body = " | ".join(join_symbols(rhs) or EPSILON for rhs in self.rules[lhs])
                lines.append(f"{lhs} → {body}")
        return "\n".join(lines)
