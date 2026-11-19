"""Pumping Lemma Explorer (FORM-03): навчальний асистент для леми про накачку КВ-мов.

Лема: якщо L — КВ-мова, то існує k, таке що для кожного t ∈ L, |t| ≥ k, знайдеться розклад
t = u t₁ x t₂ v з |t₁t₂| ≥ 1, |t₁xt₂| ≤ k та u t₁ⁱ x t₂ⁱ v ∈ L для всіх i ≥ 0.

Інструмент перебирає ВСІ розклади даного слова для даного k й перевіряє накачку для
i = 0…max_i. Це лише асистент: скінченна перевірка (одне слово, одне k, обмежене i) не є
доведенням. Щоб довести, що мова не КВ, слово має бути задане як функція від довільного k
і для нього треба довести, що жоден розклад не накачується (див. ПР6, п. 4).
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from dataclasses import dataclass, field

from sipl.formal.chomsky import to_chomsky
from sipl.formal.grammar import EPSILON, Grammar, is_nonterminal

Member = Callable[[str], bool]

DISCLAIMER = (
    "Увага: це навчальний асистент, а не універсальний розв'язувач. Перевіряється одне слово, "
    "одне k та i ≤ max_i; це не доводить ні належності мови до КВ, ні її неналежності."
)


@dataclass(frozen=True)
class Decomposition:
    u: str
    t1: str
    x: str
    t2: str
    v: str

    @property
    def word(self) -> str:
        return self.u + self.t1 + self.x + self.t2 + self.v

    def pump(self, i: int) -> str:
        return self.u + self.t1 * i + self.x + self.t2 * i + self.v

    def marked(self) -> str:
        return " | ".join(part or EPSILON for part in (self.u, self.t1, self.x, self.t2, self.v))


def decompositions(word: str, k: int) -> Iterator[Decomposition]:
    """Усі розклади з |t₁t₂| ≥ 1 та |t₁xt₂| ≤ k."""
    n = len(word)
    for a in range(n + 1):
        for d in range(a, min(n, a + k) + 1):
            for b in range(a, d + 1):
                for c in range(b, d + 1):
                    if (b - a) + (d - c) >= 1:
                        yield Decomposition(word[:a], word[a:b], word[b:c], word[c:d], word[d:])


@dataclass
class Verdict:
    decomposition: Decomposition
    failed_i: int | None  # найменше i, для якого накачане слово не в L; None — накачується

    @property
    def pumps(self) -> bool:
        return self.failed_i is None

    def to_dict(self) -> dict:
        d = self.decomposition
        data = {"u": d.u, "t1": d.t1, "x": d.x, "t2": d.t2, "v": d.v, "pumps": self.pumps}
        if self.failed_i is not None:
            data["failed_i"] = self.failed_i
            data["pumped_word"] = d.pump(self.failed_i)
        return data


def check(decomposition: Decomposition, is_member: Member, max_i: int = 4) -> Verdict:
    for i in range(max_i + 1):
        if not is_member(decomposition.pump(i)):
            return Verdict(decomposition, i)
    return Verdict(decomposition, None)


@dataclass
class Exploration:
    word: str
    k: int
    max_i: int
    in_language: bool
    verdicts: list[Verdict] = field(default_factory=list)

    @property
    def good(self) -> list[Verdict]:
        return [v for v in self.verdicts if v.pumps]

    @property
    def bad(self) -> list[Verdict]:
        return [v for v in self.verdicts if not v.pumps]

    @property
    def witness(self) -> bool:
        """Слово «ламає» лему для цього k: жоден розклад не накачується."""
        return self.in_language and len(self.word) >= self.k and not self.good


def explore(word: str, k: int, is_member: Member, max_i: int = 4) -> Exploration:
    if k < 1:
        raise ValueError("k має бути додатним")
    result = Exploration(word, k, max_i, is_member(word))
    result.verdicts = [check(d, is_member, max_i) for d in decompositions(word, k)]
    return result


# ------------------------------------------------------------ належність слова


def grammar_member(grammar: Grammar) -> Member:
    """Предикат w ∈ L(G) для КВ-граматики: CYK по нормальній формі Хомського з бібліотеки."""
    outcome = to_chomsky(grammar)
    cnf = outcome.grammar
    terminal_rules: dict[str, set[str]] = {}
    binary: list[tuple[str, str, str]] = []
    for lhs, rhs in cnf.all_rules():
        if len(rhs) == 1 and not is_nonterminal(rhs[0]):
            terminal_rules.setdefault(rhs[0], set()).add(lhs)
        elif len(rhs) == 2 and all(is_nonterminal(s) for s in rhs):
            binary.append((lhs, rhs[0], rhs[1]))
    cache: dict[str, bool] = {}

    def member(word: str) -> bool:
        if word in cache:
            return cache[word]
        if word == "":
            answer = outcome.empty_word
        else:
            n = len(word)
            table = [[set() for _ in range(n + 1)] for _ in range(n)]
            for i, ch in enumerate(word):
                table[i][1] = set(terminal_rules.get(ch, ()))
            for length in range(2, n + 1):
                for i in range(n - length + 1):
                    cell = table[i][length]
                    for split in range(1, length):
                        left, right = table[i][split], table[i + split][length - split]
                        if left and right:
                            cell.update(a for a, b, c in binary if b in left and c in right)
            answer = cnf.start in table[0][n]
        cache[word] = answer
        return answer

    return member


def _pr6(w: str) -> bool:  # a^(3n) b d^(2n) c^n
    n = w.count("c")
    return w == "a" * (3 * n) + "b" + "d" * (2 * n) + "c" * n


NAMED_LANGUAGES: dict[str, tuple[str, Member]] = {
    "anbn": ("{ aⁿbⁿ }", lambda w: w == "a" * (len(w) // 2) + "b" * (len(w) // 2)),
    "anbncn": ("{ aⁿbⁿcⁿ }", lambda w: len(w) % 3 == 0 and w == "a" * (len(w) // 3) + "b" * (len(w) // 3) + "c" * (len(w) // 3)),
    "ww": ("{ ww }", lambda w: len(w) % 2 == 0 and w[: len(w) // 2] == w[len(w) // 2 :]),
    "pr6": ("{ a³ⁿ b d²ⁿ cⁿ } (ПР6, варіант 15)", _pr6),
}

_SAFE = {"len": len, "set": set, "all": all, "any": any, "sum": sum, "range": range, "min": min, "max": max}


def expression_member(expression: str) -> Member:
    """Предикат із виразу Python над змінною w, наприклад "w.count('a') == w.count('b')".
    Це локальний інструмент: вираз виконується без доступу до builtins, окрім невеликого набору."""
    code = compile(expression, "<lang>", "eval")
    return lambda w: bool(eval(code, {"__builtins__": {}, **_SAFE, "w": w}))  # noqa: S307


def word_from_expression(expression: str, k: int) -> str:
    code = compile(expression, "<word>", "eval")
    value = eval(code, {"__builtins__": {}, **_SAFE, "k": k})  # noqa: S307
    if not isinstance(value, str):
        raise ValueError("--word-expr має повертати рядок")
    return value
