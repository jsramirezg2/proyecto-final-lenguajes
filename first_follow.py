from collections.abc import Iterable

from grammar import END_MARKER, EPSILON, Grammar


def first_of_sequence(
    symbols: Iterable[str], first: dict[str, set[str]]
) -> set[str]:
    result = set()
    for symbol in symbols:
        symbol_first = first[symbol]
        result.update(symbol_first - {EPSILON})
        if EPSILON not in symbol_first:
            return result
    result.add(EPSILON)
    return result


def compute_first(grammar: Grammar) -> dict[str, set[str]]:
    first = {symbol: {symbol} for symbol in grammar.terminals}
    first.update({symbol: set() for symbol in grammar.nonterminals})

    changed = True
    while changed:
        changed = False
        for production in grammar.productions:
            additions = first_of_sequence(production.body, first) - first[production.head]
            if additions:
                first[production.head].update(additions)
                changed = True
    return first


def compute_follow(
    grammar: Grammar, first: dict[str, set[str]]
) -> dict[str, set[str]]:
    follow = {symbol: set() for symbol in grammar.nonterminals}
    follow[grammar.start].add(END_MARKER)

    changed = True
    while changed:
        changed = False
        for production in grammar.productions:
            for index, symbol in enumerate(production.body):
                if symbol not in grammar.nonterminals:
                    continue
                suffix_first = first_of_sequence(production.body[index + 1:], first)
                additions = suffix_first - {EPSILON}
                if EPSILON in suffix_first:
                    additions.update(follow[production.head])
                additions.difference_update(follow[symbol])
                if additions:
                    follow[symbol].update(additions)
                    changed = True
    return follow
