from dataclasses import dataclass, field
from typing import TextIO

EPSILON = "e"
END_MARKER = "$"


@dataclass(frozen=True)
class Production:
    head: str
    body: tuple[str, ...]


@dataclass(frozen=True)
class Grammar:
    nonterminals: frozenset[str]
    terminals: frozenset[str]
    productions: tuple[Production, ...]
    start: str = field(default="S", init=False)


def read_grammar(stream: TextIO) -> Grammar:
    count = int(stream.readline())
    if count <= 0:
        raise ValueError("The number of nonterminals must be positive.")

    nonterminals = set()
    productions = []
    for _ in range(count):
        head, arrow, alternatives = stream.readline().partition("->")
        head = head.strip()
        bodies = alternatives.split()
        if not arrow or len(head) != 1 or not head.isalpha() or not head.isupper() or not bodies:
            raise ValueError("Expected an uppercase head and at least one alternative.")
        if head in nonterminals:
            raise ValueError(f"Repeated production head: {head}")
        nonterminals.add(head)
        for alternative in bodies:
            if alternative == EPSILON:
                productions.append(Production(head, ()))
                continue
            if EPSILON in alternative or END_MARKER in alternative:
                raise ValueError("Reserved symbols cannot appear in a production body.")
            productions.append(Production(head, tuple(alternative)))

    if "S" not in nonterminals:
        raise ValueError("Missing start symbol S.")
    terminals = set()
    for production in productions:
        for symbol in production.body:
            if symbol in nonterminals:
                continue
            if symbol.isupper():
                raise ValueError(f"Undefined nonterminal: {symbol}")
            terminals.add(symbol)

    return Grammar(frozenset(nonterminals), frozenset(terminals), tuple(productions))
