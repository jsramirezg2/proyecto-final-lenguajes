from collections.abc import Callable
from dataclasses import dataclass
from itertools import combinations

from first_follow import first_of_sequence
from grammar import END_MARKER, EPSILON, Grammar, Production


@dataclass(frozen=True)
class LL1Conflict:
    productions: tuple[Production, Production]
    reason: str
    lookaheads: frozenset[str]


@dataclass
class LL1Table:
    cells: dict[tuple[str, str], list[Production]]
    conflicts: list[LL1Conflict]

    @property
    def is_ll1(self) -> bool:
        return not self.conflicts


def build_ll1_table(
    grammar: Grammar, first: dict[str, set[str]], follow: dict[str, set[str]]
) -> LL1Table:
    cells = {}
    first_by_head = {symbol: {} for symbol in grammar.nonterminals}
    for production in grammar.productions:
        alternatives = first_by_head[production.head]
        if production in alternatives:
            continue  # Identical productions denote the same alternative.
        body_first = first_of_sequence(production.body, first)
        alternatives[production] = body_first

        lookaheads = body_first - {EPSILON}
        if EPSILON in body_first:
            lookaheads.update(follow[production.head])
        for lookahead in sorted(lookaheads):
            cells.setdefault((production.head, lookahead), []).append(production)

    conflicts = []
    for head, alternatives in first_by_head.items():
        for (left, left_first), (right, right_first) in combinations(alternatives.items(), 2):
            productions = (left, right)
            common_first = (left_first & right_first) - {EPSILON}
            if common_first:
                conflicts.append(LL1Conflict(productions, "FIRST/FIRST", frozenset(common_first)))

            both_nullable = EPSILON in left_first and EPSILON in right_first
            if both_nullable:
                conflicts.append(LL1Conflict(
                    productions, "multiple nullable alternatives", frozenset(follow[head])
                ))

            first_follow = set()
            if EPSILON in left_first:
                first_follow.update(right_first & follow[head])
            if EPSILON in right_first:
                first_follow.update(left_first & follow[head])
            if first_follow:
                conflicts.append(LL1Conflict(productions, "FIRST/FOLLOW", frozenset(first_follow)))

    return LL1Table(cells, conflicts)


def parse_ll1(
    grammar: Grammar,
    table: LL1Table,
    text: str,
    trace: Callable[[tuple[str, ...], str, str], None] | None = None,
    *,
    on_production: Callable[[Production], None] | None = None,
) -> bool:
    if not table.is_ll1:
        raise ValueError("Predictive parsing requires an LL(1) grammar.")

    text = "" if text == EPSILON else text
    if any(symbol not in grammar.terminals for symbol in text):
        return False
    buffer = text + END_MARKER
    position = 0
    stack = [END_MARKER, grammar.start]
    while stack:
        top = stack[-1]
        lookahead = buffer[position]
        if top in grammar.nonterminals:
            candidates = table.cells.get((top, lookahead))
            if not candidates:
                return False
            production, = candidates
            if on_production is not None:
                on_production(production)
            if trace is not None:
                body = "".join(production.body) or EPSILON
                trace(tuple(stack), buffer[position:], f"{top} -> {body}")
            stack.pop()
            stack.extend(reversed(production.body))
        else:
            if top != lookahead:
                return False
            if trace is not None:
                trace(tuple(stack), buffer[position:], f"match {top}")
            stack.pop()
            position += 1
    return position == len(buffer)
