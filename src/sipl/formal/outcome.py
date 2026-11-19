from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field

from sipl.formal.grammar import Grammar

SUBSCRIPTS = str.maketrans("0123456789", "₀₁₂₃₄₅₆₇₈₉")


@dataclass
class Outcome:
    grammar: Grammar
    steps: list[str] = field(default_factory=list)
    empty_word: bool = False


def subscript(number: int) -> str:
    return str(number).translate(SUBSCRIPTS)


def format_set(items: Iterable[str], order: list[str]) -> str:
    present = set(items)
    return "{" + ", ".join(s for s in order if s in present) + "}"
