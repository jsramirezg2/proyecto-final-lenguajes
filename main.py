import argparse
import sys
from functools import partial

from first_follow import compute_first, compute_follow
from grammar import END_MARKER, EPSILON, read_grammar
from ll1 import build_ll1_table, parse_ll1
from sdd import CircularSDD, build_tree, dependency_graph, evaluate, walk_tree
from sdd_example import GRAMMAR, MAIN_ATTRIBUTE, RULES
from slr import build_slr_table, parse_slr


def format_set(symbols: set[str]) -> str:
    ordered = sorted(symbols - {EPSILON, END_MARKER})
    ordered.extend(symbol for symbol in (EPSILON, END_MARKER) if symbol in symbols)
    return "{" + ", ".join(ordered) + "}"


def read_strings(stream):
    for line in stream:
        text = line.rstrip("\r\n")  # also accepts Windows line endings
        if not text:
            break
        yield text


def run_batch(parse):
    for text in read_strings(sys.stdin):
        print("yes" if parse(text) else "no")


def run_sdd(strings, rules=RULES):
    first = compute_first(GRAMMAR)
    table = build_ll1_table(GRAMMAR, first, compute_follow(GRAMMAR, first))
    for text in strings:
        root = build_tree(GRAMMAR, table, text)
        if root is None:
            print("no")
            continue
        graph = dependency_graph(root, rules)
        try:
            order = evaluate(graph)
        except CircularSDD as error:
            print(error)
            return
        for number, (node, depth) in enumerate(walk_tree(root)):
            attributes = ", ".join(f"{name}={value!r}" for name, value in sorted(node.attributes.items()))
            print("  " * depth + f"{node.symbol}[{number}] {attributes}")
            if node.production is not None and not node.production.body:
                print("  " * (depth + 1) + "ε")
        print("Evaluation order:", " -> ".join(f"{i}.{name}" for i, name in order))
        print(f"S.{MAIN_ATTRIBUTE} = {root.attributes[MAIN_ATTRIBUTE]}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Classify grammars and parse strings.")
    parser.add_argument("--sets", action="store_true", help="print FIRST and FOLLOW")
    parser.add_argument("--sdd", action="store_true", help="evaluate the example SDD")
    args = parser.parse_args()
    sys.stdout.reconfigure(line_buffering=True)  # flush each answer, even through a pipe
    if args.sdd:
        if args.sets:
            parser.error("--sdd and --sets are separate modes")
        run_sdd(read_strings(sys.stdin))
        return

    try:
        grammar = read_grammar(sys.stdin)
    except ValueError as error:
        parser.error(str(error))
    first = compute_first(grammar)
    follow = compute_follow(grammar, first)

    if args.sets:
        for label, sets in (("First", first), ("Follow", follow)):
            for symbol in sorted(grammar.nonterminals):
                print(f"{label}({symbol}) = {format_set(sets[symbol])}")

    ll1 = build_ll1_table(grammar, first, follow)
    slr = build_slr_table(grammar, follow)
    top_down = partial(parse_ll1, grammar, ll1)
    bottom_up = partial(parse_slr, grammar, slr)

    if ll1.is_ll1 and slr.is_slr1:
        parsers = {"T": top_down, "B": bottom_up}
        while True:
            print("Select a parser (T: for LL(1), B: for SLR(1), Q: quit):")
            choice = sys.stdin.readline()
            if not choice or choice.strip() == "Q":
                return
            if choice.strip() in parsers:
                run_batch(parsers[choice.strip()])
    elif ll1.is_ll1:
        print("Grammar is LL(1).")
        run_batch(top_down)
    elif slr.is_slr1:
        print("Grammar is SLR(1).")
        run_batch(bottom_up)
    else:
        print("Grammar is neither LL(1) nor SLR(1).")


if __name__ == "__main__":
    main()
