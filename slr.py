from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import Literal

from grammar import END_MARKER, EPSILON, Grammar, Production


@dataclass(frozen=True)
class Item:
    production: Production
    dot: int = 0

    @property
    def next_symbol(self) -> str | None:
        if self.dot < len(self.production.body):
            return self.production.body[self.dot]
        return None


def closure(items: Iterable[Item], productions: tuple[Production, ...]) -> frozenset[Item]:
    result = set(items)
    pending = list(result)
    expanded = set()
    while pending:
        symbol = pending.pop().next_symbol
        if symbol is None or symbol in expanded:
            continue
        expanded.add(symbol)
        for production in productions:
            if production.head == symbol:
                item = Item(production)
                if item not in result:
                    result.add(item)
                    pending.append(item)
    return frozenset(result)


def goto(
    items: frozenset[Item], symbol: str, productions: tuple[Production, ...]
) -> frozenset[Item]:
    return closure(
        (Item(item.production, item.dot + 1) for item in items if item.next_symbol == symbol),
        productions,
    )


def canonical_collection(grammar: Grammar):
    augmented = Production("S'", (grammar.start,))
    productions = (augmented,) + grammar.productions
    states = [closure([Item(augmented)], productions)]
    state_numbers = {states[0]: 0}
    transitions = {}
    symbols = sorted(grammar.nonterminals | grammar.terminals)
    for state, items in enumerate(states):
        for symbol in symbols:
            target = goto(items, symbol, productions)
            if not target:
                continue
            if target not in state_numbers:
                state_numbers[target] = len(states)
                states.append(target)
            transitions[state, symbol] = state_numbers[target]
    return augmented, states, transitions


@dataclass(frozen=True)
class Action:
    kind: Literal["shift", "reduce", "accept"]
    target: int | Production | None = None


@dataclass
class SLRTable:
    states: list[frozenset[Item]]
    transitions: dict[tuple[int, str], int]
    action: dict[tuple[int, str], set[Action]]
    goto: dict[tuple[int, str], int]

    @property
    def conflicts(self) -> dict[tuple[int, str], set[Action]]:
        return {cell: actions for cell, actions in self.action.items() if len(actions) > 1}

    @property
    def is_slr1(self) -> bool:
        return not self.conflicts


def build_slr_table(grammar: Grammar, follow: dict[str, set[str]]) -> SLRTable:
    augmented, states, transitions = canonical_collection(grammar)
    action = {}
    nonterminal_goto = {}
    for (state, symbol), target in transitions.items():
        if symbol in grammar.terminals:
            action.setdefault((state, symbol), set()).add(Action("shift", target))
        else:
            nonterminal_goto[state, symbol] = target

    for state, items in enumerate(states):
        for item in items:
            if item.next_symbol is not None:
                continue
            production = item.production
            if production == augmented:
                action.setdefault((state, END_MARKER), set()).add(Action("accept"))
            else:
                for symbol in follow[production.head]:
                    action.setdefault((state, symbol), set()).add(Action("reduce", production))

    return SLRTable(states, transitions, action, nonterminal_goto)


def parse_slr(
    grammar: Grammar, table: SLRTable, text: str,
    trace: Callable[[tuple[int, ...], str, Action], None] | None = None,
) -> bool:
    if not table.is_slr1:
        raise ValueError("LR parsing requires a conflict-free SLR table.")
    text = "" if text == EPSILON else text
    if any(symbol not in grammar.terminals for symbol in text):
        return False

    buffer = text + END_MARKER
    position = 0
    stack = [0]
    while True:
        actions = table.action.get((stack[-1], buffer[position]))
        if not actions:
            return False
        action, = actions
        if trace is not None:
            trace(tuple(stack), buffer[position:], action)
        if action.kind == "shift":
            stack.append(action.target)
            position += 1
        elif action.kind == "reduce":
            production = action.target
            if production.body:
                del stack[-len(production.body):]
            stack.append(table.goto[stack[-1], production.head])
        else:
            return position == len(text)
