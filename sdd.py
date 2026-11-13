from collections import deque
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field

from grammar import Grammar, Production
from ll1 import LL1Table, parse_ll1

Attribute = tuple[int, str]


@dataclass
class Node:
    symbol: str
    production: Production | None = None
    children: list["Node"] = field(default_factory=list)
    attributes: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class Rule:
    # Position zero is the production head. Body positions start at one.
    target: Attribute
    dependencies: tuple[Attribute, ...]
    compute: Callable[..., object]


class CircularSDD(ValueError):
    pass


def build_tree(grammar: Grammar, table: LL1Table, text: str) -> Node | None:
    derivation = []
    if not parse_ll1(grammar, table, text, on_production=derivation.append):
        return None

    root = Node(grammar.start)
    pending = [root]
    for production in derivation:
        node = pending.pop()
        node.production = production
        node.children = [Node(symbol) for symbol in production.body]
        for child in reversed(node.children):
            if child.symbol in grammar.nonterminals:
                pending.append(child)
            else:
                child.attributes["lexval"] = child.symbol
    return root


def walk_tree(root: Node) -> Iterator[tuple[Node, int]]:
    pending = [(root, 0)]
    while pending:
        node, depth = pending.pop()
        yield node, depth
        pending.extend((child, depth + 1) for child in reversed(node.children))


@dataclass
class DependencyGraph:
    nodes: list[Node]
    rules: dict[Attribute, Rule]
    edges: dict[Attribute, list[Attribute]]


def dependency_graph(
    root: Node, rules_by_production: dict[Production, tuple[Rule, ...]]
) -> DependencyGraph:
    nodes = [node for node, _ in walk_tree(root)]
    node_numbers = {id(node): number for number, node in enumerate(nodes)}
    edges = {}
    rules = {}
    for number, node in enumerate(nodes):
        if node.production is None:
            edges[number, "lexval"] = []
            continue
        positions = [number] + [node_numbers[id(child)] for child in node.children]
        for rule in rules_by_production[node.production]:
            position, name = rule.target
            target = positions[position], name
            if target in rules:
                raise ValueError(f"Attribute defined twice: {target}")
            dependencies = tuple((positions[index], attr) for index, attr in rule.dependencies)
            rules[target] = Rule(target, dependencies, rule.compute)
            edges[target] = []

    for target, rule in rules.items():
        for dependency in dict.fromkeys(rule.dependencies):
            if dependency not in edges:
                raise ValueError(f"Undefined dependency: {dependency}")
            edges[dependency].append(target)
    return DependencyGraph(nodes, rules, edges)


def evaluate(graph: DependencyGraph) -> list[Attribute]:
    incoming = dict.fromkeys(graph.edges, 0)
    for targets in graph.edges.values():
        for target in targets:
            incoming[target] += 1
    ready = deque(vertex for vertex, degree in incoming.items() if degree == 0)

    order = []
    while ready:
        vertex = ready.popleft()
        order.append(vertex)
        for target in graph.edges[vertex]:
            incoming[target] -= 1
            if incoming[target] == 0:
                ready.append(target)
    if len(order) != len(incoming):
        raise CircularSDD("SDD is circular.")

    for vertex in order:
        if vertex in graph.rules:
            rule = graph.rules[vertex]
            values = [graph.nodes[index].attributes[name] for index, name in rule.dependencies]
            index, name = vertex
            graph.nodes[index].attributes[name] = rule.compute(*values)
    return order
