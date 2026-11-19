"""Системи рівнянь над формальними мовами та їх ітеративні наближення (FORM-02).

Система E: X = t₁ ∪ t₂ ∪ …, де кожен доданок tᵢ — конкатенація одноелементних мов
({aaa}) і змінних. Це та сама нотація, що й у практичній роботі 5:

    S = {aaa}A
    A = {dd}A{c} ∪ {ε}

Розв'язок R(E) — найменша нерухома точка, тобто ⋃ₖ Xₖ, де X₀ = ∅, а Xₖ₊₁ береться з Xₖ
одночасно для всіх змінних. Для довільного ліміту довжини L обрізання слів довшими за L
не псує слова довжини ≤ L: конкатенація ніколи не вкорочує слово.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field

from sipl.formal.grammar import (
    EPSILON,
    PRIME,
    Grammar,
    GrammarSyntaxError,
    Rule,
    is_nonterminal,
    join_symbols,
    tokenize,
)
from sipl.formal.language import concatenations, language_up_to
from sipl.formal.outcome import subscript

EMPTY_SET = "∅"
UNION = "∪"


class EquationSyntaxError(GrammarSyntaxError):
    pass


# ---------------------------------------------------------------- форматування


def format_term(rhs: Rule, index: int | None = None) -> str:
    """{aa}A{c}; якщо задано index, змінні дістають нижній індекс: {aa}A₃{c}."""
    parts: list[str] = []
    block: list[str] = []
    for symbol in rhs:
        if is_nonterminal(symbol):
            if block:
                parts.append("{" + join_symbols(tuple(block)) + "}")
                block = []
            parts.append(symbol if index is None else symbol + subscript(index))
        else:
            block.append(symbol)
    if block:
        parts.append("{" + join_symbols(tuple(block)) + "}")
    return "".join(parts) or "{" + EPSILON + "}"


def format_expression(alternatives: list[Rule], index: int | None = None) -> str:
    if not alternatives:
        return EMPTY_SET
    return f" {UNION} ".join(format_term(rhs, index) for rhs in alternatives)


def sort_words(words: Iterable[str]) -> list[str]:
    return sorted(words, key=lambda w: (len(w), w))


def format_words(words: Iterable[str], limit: int | None = None) -> str:
    ordered = sort_words(words)
    if not ordered:
        return EMPTY_SET
    shown = ordered if limit is None else ordered[:limit]
    text = ", ".join(w or EPSILON for w in shown)
    if limit is not None and len(ordered) > limit:
        text += f", … (+{len(ordered) - limit})"
    return "{" + text + "}"


# ---------------------------------------------------------------------- розбір


def _split_top(text: str, separators: str) -> list[str]:
    parts, depth, current = [], 0, []
    for ch in text:
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
        if depth == 0 and ch in separators:
            parts.append("".join(current))
            current = []
        else:
            current.append(ch)
    parts.append("".join(current))
    return parts


def _parse_term(text: str, line: int) -> Rule | None:
    """Повертає правило або None, якщо добуток містить ∅ (такий доданок дає порожню мову)."""
    text = text.strip()
    if not text:
        raise EquationSyntaxError(f"рядок {line}: порожній доданок")
    result: list[str] = []
    is_empty = False
    i = 0
    while i < len(text):
        ch = text[i]
        if ch.isspace():
            i += 1
        elif ch == "{":
            j = text.find("}", i)
            if j < 0:
                raise EquationSyntaxError(f"рядок {line}: немає закривної дужки в «{text}»")
            inner = text[i + 1 : j]
            if not inner.strip():
                raise EquationSyntaxError(
                    f"рядок {line}: порожні дужки {{}}; пишіть {{ε}} для порожнього слова або ∅ для порожньої мови"
                )
            word = tokenize(inner, line)
            if any(is_nonterminal(s) for s in word):
                raise EquationSyntaxError(f"рядок {line}: у {{…}} мають бути лише термінали, а там «{inner}»")
            result.extend(word)
            i = j + 1
        elif ch == EMPTY_SET:
            is_empty = True
            i += 1
        elif ch.isalpha() and ch.isupper():
            name = ch
            i += 1
            while i < len(text) and text[i] in (PRIME, "'"):
                name += PRIME
                i += 1
            result.append(name)
        elif ch.isalpha():
            result.append(ch)
            i += 1
        else:
            raise EquationSyntaxError(f"рядок {line}: неочікуваний символ «{ch}» у «{text}»")
    return None if is_empty else tuple(result)


@dataclass
class EquationSystem:
    start: str
    equations: dict[str, list[Rule]] = field(default_factory=dict)

    # --- побудова ---

    @classmethod
    def from_text(cls, text: str, start: str | None = None) -> EquationSystem:
        system = cls(start or "")
        for number, raw in enumerate(text.splitlines(), start=1):
            for part in _split_top(raw.split("#", 1)[0], ",;"):
                if not part.strip():
                    continue
                if "=" not in part:
                    raise EquationSyntaxError(f"рядок {number}: немає «=» у рівнянні «{part.strip()}»")
                left, right = part.split("=", 1)
                name = tokenize(left, number)
                if len(name) != 1 or not is_nonterminal(name[0]):
                    raise EquationSyntaxError(
                        f"рядок {number}: ліворуч від «=» має бути одна змінна, а там «{left.strip()}»"
                    )
                variable = name[0]
                if not system.start:
                    system.start = variable
                alternatives = system.equations.setdefault(variable, [])
                for summand in _split_top(right, f"{UNION}|"):
                    if summand.strip() == EMPTY_SET:
                        continue
                    rhs = _parse_term(summand, number)
                    if rhs is not None and rhs not in alternatives:
                        alternatives.append(rhs)
        if not system.equations:
            raise EquationSyntaxError("система не містить жодного рівняння")
        system.validate()
        return system

    @classmethod
    def from_grammar(cls, grammar: Grammar) -> EquationSystem:
        """Правила X → α₁ | α₂ стають рівнянням X = α₁ ∪ α₂; нетермінал без правил дає X = ∅."""
        equations = {nt: list(grammar.alternatives(nt)) for nt in grammar.nonterminals()}
        return cls(grammar.start, equations)

    def to_grammar(self) -> Grammar:
        grammar = Grammar(self.start)
        for lhs, alternatives in self.equations.items():
            for rhs in alternatives:
                grammar.add_rule(lhs, rhs)
        return grammar

    def validate(self) -> None:
        if self.start not in self.equations:
            raise EquationSyntaxError(f"для початкової змінної «{self.start}» немає рівняння")
        missing = [v for v in self.variables() if v not in self.equations]
        if missing:
            raise EquationSyntaxError("немає рівнянь для змінних: " + ", ".join(missing))

    # --- доступ ---

    def variables(self) -> list[str]:
        ordered = [self.start]
        ordered.extend(v for v in self.equations if v != self.start)
        for alternatives in self.equations.values():
            for rhs in alternatives:
                for symbol in rhs:
                    if is_nonterminal(symbol) and symbol not in ordered:
                        ordered.append(symbol)
        return ordered

    def __str__(self) -> str:
        return "\n".join(f"{v} = {format_expression(self.equations[v])}" for v in self.variables() if v in self.equations)


# ------------------------------------------------------------------ наближення


@dataclass
class Approximations:
    """levels[k][X] = Xₖ (слова довжини ≤ max_length); levels[0] — усі ∅."""

    system: EquationSystem
    max_length: int
    levels: list[dict[str, frozenset[str]]]
    stable_at: int | None  # перший k, з якого Xₖ вже не змінюються (в межах max_length)

    @property
    def limit(self) -> dict[str, frozenset[str]]:
        return self.levels[-1]

    def entry_levels(self, variable: str) -> dict[str, int]:
        """Для кожного слова — номер першого наближення, у якому воно з'являється."""
        result: dict[str, int] = {}
        for k, level in enumerate(self.levels):
            for word in level[variable]:
                result.setdefault(word, k)
        return result


def step(system: EquationSystem, current: dict[str, frozenset[str]], max_length: int) -> dict[str, frozenset[str]]:
    """Один крок Xₖ₊₁ = F(Xₖ), одночасно для всіх змінних."""
    mutable = {v: set(words) for v, words in current.items()}
    new: dict[str, frozenset[str]] = {}
    for variable in system.variables():
        words: set[str] = set()
        for rhs in system.equations.get(variable, []):
            words |= concatenations(rhs, mutable, max_length)
        new[variable] = frozenset(words)
    return new


def approximate(system: EquationSystem, max_length: int, max_steps: int = 200) -> Approximations:
    if max_length < 0:
        raise ValueError("max_length має бути невід'ємним")
    current: dict[str, frozenset[str]] = {v: frozenset() for v in system.variables()}
    levels = [current]
    stable_at: int | None = None
    for _ in range(max_steps):
        following = step(system, current, max_length)
        if following == current:
            stable_at = len(levels) - 1
            break
        levels.append(following)
        current = following
    return Approximations(system, max_length, levels, stable_at)


def explain(result: Approximations, steps: int | None = None, show_words: int | None = 8) -> list[str]:
    """Покроковий запис: Xₖ = рівняння з підставленими Xₖ₋₁ = обчислені слова."""
    system = result.system
    last = len(result.levels) - 1 if steps is None else min(steps, len(result.levels) - 1)
    lines = ["-- Крок 0 (початок: усі змінні = ∅)"]
    for variable in system.variables():
        lines.append(f"{variable}{subscript(0)} = {EMPTY_SET}")
    for k in range(1, last + 1):
        lines.append(f"-- Крок {k}")
        for variable in system.variables():
            expression = format_expression(system.equations.get(variable, []), k - 1)
            words = format_words(result.levels[k][variable], show_words)
            lines.append(f"{variable}{subscript(k)} = {expression} = {words}")
    return lines


# ---------------------------------------------------------------- порівняння


@dataclass
class Comparison:
    variable: str
    equal: bool
    only_in_equations: list[str]
    only_in_grammar: list[str]

    def to_dict(self) -> dict:
        return {
            "variable": self.variable,
            "equal": self.equal,
            "only_in_equations": self.only_in_equations,
            "only_in_grammar": self.only_in_grammar,
        }


def compare_with_grammar(result: Approximations, grammar: Grammar) -> list[Comparison]:
    """Порівнює R(E) із L(G) для слів довжини ≤ max_length: для кожної змінної, що є в граматиці."""
    comparisons = []
    names = set(grammar.nonterminals())
    for variable in result.system.variables():
        if variable not in names:
            continue
        theirs = language_up_to(Grammar(variable, grammar.rules), result.max_length)
        ours = set(result.limit[variable])
        comparisons.append(
            Comparison(variable, ours == theirs, sort_words(ours - theirs), sort_words(theirs - ours))
        )
    return comparisons


# ------------------------------------------------- конструктор родини мов


@dataclass(frozen=True)
class Family:
    """Мова {p xⁿ m yⁿ s | n ≥ 0}; практична робота 5: p=aaa, x=dd, m=ε, y=c, s=ε."""

    prefix: str = ""
    left: str = ""
    middle: str = ""
    right: str = ""
    suffix: str = ""

    def __post_init__(self) -> None:
        for name in ("prefix", "left", "middle", "right", "suffix"):
            value = getattr(self, name)
            if value == EPSILON:
                object.__setattr__(self, name, "")
            elif not all(ch.isalpha() and ch.islower() for ch in value):
                raise EquationSyntaxError(f"{name}: очікуються малі літери (термінали), а там «{value}»")
        if not self.left and not self.right:
            raise EquationSyntaxError("left і right не можуть бути одночасно порожніми: A → A не породжує нових слів")

    def describe(self) -> str:
        def power(word: str) -> str:
            return f"({word})ⁿ" if len(word) > 1 else f"{word}ⁿ"

        pieces = [self.prefix]
        pieces.append(power(self.left) if self.left else "")
        pieces.append(self.middle)
        pieces.append(power(self.right) if self.right else "")
        pieces.append(self.suffix)
        return "L = { " + "".join(pieces) + " | n ≥ 0 }"

    def grammar(self) -> Grammar:
        grammar = Grammar("S")
        grammar.add_rule("S", (*self.prefix, "A", *self.suffix))
        grammar.add_rule("A", (*self.left, "A", *self.right))
        grammar.add_rule("A", tuple(self.middle))
        return grammar

    def equations(self) -> EquationSystem:
        return EquationSystem.from_grammar(self.grammar())

    def words(self, max_length: int) -> set[str]:
        """Пряме перелічення слів без жодної граматики — незалежний еталон."""
        words = set()
        n = 0
        while True:
            length = len(self.prefix) + len(self.middle) + len(self.suffix) + n * (len(self.left) + len(self.right))
            if length > max_length:
                return words
            words.add(self.prefix + self.left * n + self.middle + self.right * n + self.suffix)
            n += 1
