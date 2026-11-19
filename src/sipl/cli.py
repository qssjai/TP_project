from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from sipl import cli_eq, cli_pump
from sipl.formal import (
    Grammar,
    GrammarSyntaxError,
    derivation_steps,
    find_trees,
    format_derivation,
    remove_epsilon_rules,
    remove_useless,
    steps_to_dicts,
    to_chomsky,
    trees_to_dot,
)
from sipl.formal.grammar import is_nonterminal, tokenize

OPERATIONS = {
    "clean": remove_useless,
    "epsilon": remove_epsilon_rules,
    "chomsky": to_chomsky,
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="sipl")
    commands = parser.add_subparsers(dest="command", required=True)
    cfg = commands.add_parser("cfg", help="перетворення КВ-граматик")
    cfg.add_argument("operation", choices=sorted(OPERATIONS))
    cfg.add_argument("file")
    cfg.add_argument("--no-steps", action="store_true", help="показати лише результат")
    derive = commands.add_parser("derive", help="виведення та дерева виводу слова")
    derive.add_argument("file")
    derive.add_argument("word", help="слово з терміналів; ε для порожнього слова")
    derive.add_argument("--depth", type=int, default=10, help="максимальна висота дерева")
    derive.add_argument("--limit", type=int, default=10, help="максимальна кількість дерев")
    derive.add_argument("--format", choices=["text", "json", "dot"], default="text")
    cli_eq.add_parser(commands)
    cli_pump.add_parser(commands)
    return parser


def run_derive(grammar: Grammar, args: argparse.Namespace) -> int:
    try:
        word = tokenize(args.word)
    except GrammarSyntaxError as error:
        print(f"Помилка в слові: {error}", file=sys.stderr)
        return 1
    if any(is_nonterminal(symbol) for symbol in word):
        print("Слово має складатися лише з терміналів", file=sys.stderr)
        return 1

    trees = find_trees(grammar, word, args.depth, args.limit)
    if args.format == "dot":
        print(trees_to_dot(trees))
        return 0
    if args.format == "json":
        data = [
            {
                "tree": tree.to_dict(),
                "leftmost": steps_to_dicts(derivation_steps(tree, leftmost=True)),
                "rightmost": steps_to_dicts(derivation_steps(tree, leftmost=False)),
            }
            for tree in trees
        ]
        print(json.dumps(data, ensure_ascii=False, indent=2))
        return 0

    if not trees:
        print(f"Дерев виводу не знайдено (висота ≤ {args.depth}).")
        return 0
    print(f"Знайдено дерев: {len(trees)} (висота ≤ {args.depth})")
    for index, tree in enumerate(trees, start=1):
        print(f"\nДерево {index}:")
        print(tree.to_text())
        print("\nЛівостороннє виведення:")
        print(format_derivation(derivation_steps(tree, leftmost=True)))
        print("\nПравостороннє виведення:")
        print(format_derivation(derivation_steps(tree, leftmost=False)))
    if len(trees) >= 2:
        print("\nДля цього слова існує кілька дерев, тож граматика неоднозначна.")
    if len(trees) >= args.limit:
        print(f"Досягнуто ліміт у {args.limit} дерев, їх може бути більше.")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "eq":
        return cli_eq.run(args)
    if args.command == "pump":
        return cli_pump.run(args)
    try:
        grammar = Grammar.from_text(Path(args.file).read_text(encoding="utf-8"))
    except OSError as error:
        print(f"Не вдалося прочитати файл: {error}", file=sys.stderr)
        return 2
    except GrammarSyntaxError as error:
        print(f"Помилка в граматиці: {error}", file=sys.stderr)
        return 1

    if args.command == "derive":
        return run_derive(grammar, args)

    outcome = OPERATIONS[args.operation](grammar)
    if not args.no_steps:
        print("\n".join(outcome.steps))
        print()
    print(str(outcome.grammar) or "(правил немає)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
