"""Підкоманда `sipl pump`: Pumping Lemma Explorer (FORM-03).

Коди завершення: 0 — успіх; 1 — помилка в аргументах/граматиці/виразі; 2 — файл не прочитано.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from sipl.formal import Grammar, GrammarSyntaxError
from sipl.formal.grammar import EPSILON
from sipl.formal.pumping import (
    DISCLAIMER,
    NAMED_LANGUAGES,
    Decomposition,
    Exploration,
    check,
    explore,
    expression_member,
    grammar_member,
    word_from_expression,
)


def add_parser(commands) -> None:
    p = commands.add_parser("pump", help="Pumping Lemma Explorer: розклади uvwxy та перевірка накачки")
    lang = p.add_mutually_exclusive_group(required=True)
    lang.add_argument("--grammar", metavar="ФАЙЛ", help="мова як КВ-граматика (перевірка CYK)")
    lang.add_argument("--lang", choices=sorted(NAMED_LANGUAGES), help="готова мова")
    lang.add_argument("--pred", metavar="ВИРАЗ", help="предикат Python над w, напр. \"w.count('a')==w.count('b')\"")
    word = p.add_mutually_exclusive_group(required=True)
    word.add_argument("--word", help="слово t")
    word.add_argument("--word-expr", metavar="ВИРАЗ", help="слово як вираз від k, напр. \"'a'*(3*k)+'b'+'d'*(2*k)+'c'*k\"")
    p.add_argument("-k", type=int, nargs="+", required=True, help="одне або кілька значень k з леми")
    p.add_argument("--max-i", type=int, default=4, help="максимальне i для накачки (за замовчуванням 4)")
    p.add_argument("--split", metavar="u|t1|x|t2|v", help="перевірити один розклад (ε або порожньо — порожній рядок)")
    p.add_argument("--show", type=int, default=5, help="скільки розкладів показати в кожній групі")
    p.add_argument("--format", choices=["text", "json"], default="text")


def _split(text: str) -> Decomposition:
    parts = ["" if part.strip() in ("", EPSILON) else part.strip() for part in text.split("|")]
    if len(parts) != 5:
        raise ValueError("--split має містити п'ять частин через «|»: u|t1|x|t2|v")
    return Decomposition(*parts)


def _print_exploration(e: Exploration, show: int) -> None:
    print(f"k = {e.k}, t = {e.word or EPSILON} (|t| = {len(e.word)}), i = 0…{e.max_i}")
    if not e.in_language:
        print("  Слово не належить мові: лема до нього не застосовується.")
        return
    if len(e.word) < e.k:
        print("  |t| < k: умова леми |t| ≥ k не виконана, слово не підходить.")
    total = len(e.verdicts)
    print(f"  Розкладів з |t₁t₂| ≥ 1 та |t₁xt₂| ≤ k: {total}; накачуються: {len(e.good)}; ламаються: {len(e.bad)}")
    if e.good:
        print("  Накачуються (u | t₁ | x | t₂ | v):")
        for v in e.good[:show]:
            print(f"    {v.decomposition.marked()}")
        if len(e.good) > show:
            print(f"    … ще {len(e.good) - show}")
    if e.bad:
        print("  Ламаються (перше i, для якого u t₁ⁱ x t₂ⁱ v ∉ L):")
        for v in e.bad[:show]:
            i, d = v.failed_i, v.decomposition
            print(f"    {d.marked()}   i = {i}: {d.pump(i) or EPSILON}")
        if len(e.bad) > show:
            print(f"    … ще {len(e.bad) - show}")
    if e.witness:
        print("  ⇒ Для цього k жоден розклад не накачується (в межах перевірених i).")
    elif e.good and len(e.word) >= e.k:
        print("  ⇒ Існує розклад, що накачується: це слово не спростовує КВ-властивість для цього k.")


def run(args: argparse.Namespace) -> int:
    try:
        if args.grammar:
            member = grammar_member(Grammar.from_text(Path(args.grammar).read_text(encoding="utf-8")))
        elif args.lang:
            member = NAMED_LANGUAGES[args.lang][1]
        else:
            member = expression_member(args.pred)
    except OSError as error:
        print(f"Не вдалося прочитати файл: {error}", file=sys.stderr)
        return 2
    except GrammarSyntaxError as error:
        print(f"Помилка в граматиці: {error}", file=sys.stderr)
        return 1
    except SyntaxError as error:
        print(f"Помилка у виразі: {error}", file=sys.stderr)
        return 1

    try:
        explorations = []
        for k in args.k:
            word = args.word if args.word is not None else word_from_expression(args.word_expr, k)
            if args.split:
                d = _split(args.split)
                if d.word != word:
                    raise ValueError(f"розклад дає слово «{d.word}», а не «{word}»")
                if len(d.t1 + d.t2) < 1 or len(d.t1 + d.x + d.t2) > k:
                    raise ValueError("розклад порушує |t₁t₂| ≥ 1 або |t₁xt₂| ≤ k")
                e = Exploration(word, k, args.max_i, member(word), [check(d, member, args.max_i)])
            else:
                e = explore(word, k, member, args.max_i)
            explorations.append(e)
    except (ValueError, NameError, TypeError, SyntaxError) as error:
        print(f"Помилка: {error}", file=sys.stderr)
        return 1

    if args.format == "json":
        data = {
            "disclaimer": DISCLAIMER,
            "results": [
                {
                    "k": e.k,
                    "word": e.word,
                    "in_language": e.in_language,
                    "witness": e.witness,
                    "pumps": [v.to_dict() for v in e.good],
                    "fails": [v.to_dict() for v in e.bad],
                }
                for e in explorations
            ],
        }
        print(json.dumps(data, ensure_ascii=False, indent=2))
        return 0
    print(DISCLAIMER + "\n")
    for e in explorations:
        _print_exploration(e, args.show)
        print()
    return 0
