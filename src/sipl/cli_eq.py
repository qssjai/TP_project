"""Підкоманда `sipl eq`: системи рівнянь над мовами (FORM-02).

Коди завершення: 0 — успіх; 1 — синтаксична помилка або некоректні аргументи;
2 — не вдалося прочитати файл; 3 — розв'язок системи не збігається з граматикою.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from sipl.formal import (
    EquationSyntaxError,
    EquationSystem,
    Family,
    Grammar,
    GrammarSyntaxError,
    approximate,
    compare_with_grammar,
)
from sipl.formal.equations import explain, format_words, sort_words
from sipl.formal.grammar import ARROWS, format_rule
from sipl.formal.language import language_up_to
from sipl.formal.outcome import subscript


def add_parser(commands) -> None:
    eq = commands.add_parser("eq", help="системи рівнянь над формальними мовами")
    actions = eq.add_subparsers(dest="action", required=True)

    convert = actions.add_parser("convert", help="граматика ⇄ система рівнянь")
    convert.add_argument("file")
    convert.add_argument("--kind", choices=["auto", "grammar", "equations"], default="auto")

    solve = actions.add_parser("solve", help="ітеративні наближення X₀=∅, X₁, X₂, … та розв'язок")
    solve.add_argument("file", help="файл із системою рівнянь або з граматикою")
    solve.add_argument("--kind", choices=["auto", "grammar", "equations"], default="auto")
    solve.add_argument("--max-length", type=int, default=10, help="максимальна довжина слів (за замовчуванням 10)")
    solve.add_argument("--steps", type=int, default=4, help="скільки кроків показати (за замовчуванням 4)")
    solve.add_argument("--words", type=int, default=8, help="скільки слів показувати в кожній множині")
    solve.add_argument("--compare", metavar="ГРАМАТИКА", help="порівняти розв'язок із граматикою з цього файлу")
    solve.add_argument("--entry-levels", action="store_true", help="для кожного слова початкової змінної показати, з якого кроку воно з'являється")
    solve.add_argument("--format", choices=["text", "json"], default="text")

    build = actions.add_parser("build", help="побудувати G та E для мови { p xⁿ m yⁿ s | n ≥ 0 }")
    build.add_argument("--prefix", default="", help="p (за замовчуванням порожнє)")
    build.add_argument("--left", default="", help="x")
    build.add_argument("--middle", default="", help="m")
    build.add_argument("--right", default="", help="y")
    build.add_argument("--suffix", default="", help="s")
    build.add_argument("--max-length", type=int, default=10, help="довжина для перевірки L(G) = R(E) = L")


def _looks_like_grammar(text: str) -> bool:
    body = "\n".join(line.split("#", 1)[0] for line in text.splitlines())
    return any(arrow in body for arrow in ARROWS)


def _load(path: str, kind: str) -> tuple[EquationSystem, Grammar | None]:
    text = Path(path).read_text(encoding="utf-8")
    if kind == "auto":
        kind = "grammar" if _looks_like_grammar(text) else "equations"
    if kind == "grammar":
        grammar = Grammar.from_text(text)
        return EquationSystem.from_grammar(grammar), grammar
    return EquationSystem.from_text(text), None


def run(args: argparse.Namespace) -> int:
    try:
        if args.action == "build":
            return _build(args)
        system, grammar = _load(args.file, args.kind)
        if args.action == "convert":
            return _convert(system, grammar)
        return _solve(args, system, grammar)
    except OSError as error:
        print(f"Не вдалося прочитати файл: {error}", file=sys.stderr)
        return 2
    except GrammarSyntaxError as error:  # включно з EquationSyntaxError
        kind = "у системі рівнянь" if isinstance(error, EquationSyntaxError) else "в граматиці"
        print(f"Помилка {kind}: {error}", file=sys.stderr)
        return 1


def _convert(system: EquationSystem, grammar: Grammar | None) -> int:
    if grammar is not None:
        print("Система рівнянь (X → α₁ | α₂ перетворюється на X = α₁ ∪ α₂):")
        print(system)
    else:
        print("Граматика (X = α₁ ∪ α₂ перетворюється на правила X → α₁ | α₂):")
        print(system.to_grammar() if system.to_grammar().rules else "(правил немає)")
    return 0


def _solve(args: argparse.Namespace, system: EquationSystem, grammar: Grammar | None) -> int:
    if args.max_length < 0 or args.steps < 0:
        print("--max-length і --steps мають бути невід'ємними", file=sys.stderr)
        return 1
    result = approximate(system, args.max_length)

    reference = grammar
    if args.compare:
        try:
            reference = Grammar.from_text(Path(args.compare).read_text(encoding="utf-8"))
        except OSError as error:
            print(f"Не вдалося прочитати файл: {error}", file=sys.stderr)
            return 2
    comparisons = compare_with_grammar(result, reference) if reference else []
    start_levels = result.entry_levels(system.start)

    if args.format == "json":
        data = {
            "start": system.start,
            "max_length": args.max_length,
            "equations": {v: [list(r) for r in system.equations.get(v, [])] for v in system.variables()},
            "stable_at": result.stable_at,
            "levels": [{v: sort_words(words) for v, words in level.items()} for level in result.levels],
            "solution": {v: sort_words(words) for v, words in result.limit.items()},
            "entry_levels": {w: k for w, k in sorted(start_levels.items(), key=lambda p: (len(p[0]), p[0]))},
            "comparison": [c.to_dict() for c in comparisons],
        }
        print(json.dumps(data, ensure_ascii=False, indent=2))
        return 0 if all(c.equal for c in comparisons) else 3

    print("Система рівнянь:")
    print(system)
    print(f"\nНаближення (слова довжини ≤ {args.max_length}):")
    print("\n".join(explain(result, args.steps, args.words)))
    shown = min(args.steps, len(result.levels) - 1)
    if result.stable_at is None:
        print(f"\nНерухому точку не знайдено за {len(result.levels) - 1} кроків.")
    elif shown >= result.stable_at:
        print(f"\nНерухома точка досягнута на кроці {result.stable_at}: подальші кроки нічого не змінюють.")
    else:
        print(f"\n… показано кроки до {shown}; нерухома точка (для слів ≤ {args.max_length}) досягається на кроці {result.stable_at}.")
    print(f"\nРозв'язок R(E) для слів довжини ≤ {args.max_length}:")
    for variable in system.variables():
        print(f"{variable} = {format_words(result.limit[variable], args.words)}")

    if args.entry_levels:
        print(f"\nУ якому наближенні з'являється слово ({system.start}):")
        for word, k in sorted(start_levels.items(), key=lambda p: (p[1], len(p[0]), p[0])):
            print(f"  {word or 'ε':<20} {system.start}{subscript(k)}")

    if comparisons:
        print(f"\nПорівняння з граматикою (слова довжини ≤ {args.max_length}):")
        for c in comparisons:
            if c.equal:
                print(f"  {c.variable}: R(E) = L(G) ✓")
            else:
                print(f"  {c.variable}: НЕ збігається")
                if c.only_in_equations:
                    print(f"     лише в R(E): {format_words(c.only_in_equations, 6)}")
                if c.only_in_grammar:
                    print(f"     лише в L(G): {format_words(c.only_in_grammar, 6)}")
    return 0 if all(c.equal for c in comparisons) else 3


def _build(args: argparse.Namespace) -> int:
    try:
        family = Family(args.prefix, args.left, args.middle, args.right, args.suffix)
    except EquationSyntaxError as error:
        print(f"Помилка: {error}", file=sys.stderr)
        return 1
    grammar, system = family.grammar(), family.equations()
    print(family.describe())
    print("\nКВ-граматика G:")
    for index, (lhs, rhs) in enumerate(grammar.all_rules(), start=1):
        print(f"  P{index}: {format_rule(lhs, rhs)}")
    print("\nСистема рівнянь E:")
    print(system)

    result = approximate(system, args.max_length)
    target = family.words(args.max_length)
    solution = set(result.limit[system.start])
    generated = language_up_to(grammar, args.max_length)
    print(f"\nПеревірка для слів довжини ≤ {args.max_length}: |L| = {len(target)}")
    print(f"  R(E) = L: {'так' if solution == target else 'НІ'}")
    print(f"  L(G) = L: {'так' if generated == target else 'НІ'}")
    return 0 if solution == target == generated else 3
