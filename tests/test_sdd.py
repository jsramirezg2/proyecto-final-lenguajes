from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
import subprocess
import sys
import unittest

from first_follow import compute_first, compute_follow
from grammar import Production
from ll1 import build_ll1_table
from main import run_sdd
from sdd import CircularSDD, Rule, build_tree, dependency_graph, evaluate
from sdd_example import GRAMMAR, RULES


class SDDTests(unittest.TestCase):
    def setUp(self):
        first = compute_first(GRAMMAR)
        self.table = build_ll1_table(GRAMMAR, first, compute_follow(GRAMMAR, first))

    def test_six_input_strings(self):
        for text, expected in (
            ("+", 0), ("-", 0), ("-yx", -4), ("+xyx", 8),
            ("+xz", None), ("+" + "x" * 2000, 2001000),
        ):
            with self.subTest(length=len(text), expected=expected):
                tree = build_tree(GRAMMAR, self.table, text)
                if expected is None:
                    self.assertIsNone(tree)
                else:
                    evaluate(dependency_graph(tree, RULES))
                    self.assertEqual(tree.attributes["total"], expected)

    def test_manual_graph_and_tree(self):
        root = build_tree(GRAMMAR, self.table, "+xyx")
        graph = dependency_graph(root, RULES)
        self.assertEqual(set(graph.edges), {
            (0, "total"), (1, "lexval"), (2, "step"), (2, "total"), (3, "weight"),
            (4, "lexval"), (5, "step"), (5, "total"), (6, "weight"), (7, "lexval"),
            (8, "step"), (8, "total"), (9, "weight"), (10, "lexval"),
            (11, "step"), (11, "total"),
        })
        self.assertEqual({source: set(targets) for source, targets in graph.edges.items() if targets}, {
            (2, "step"): {(5, "step"), (2, "total")},
            (5, "step"): {(8, "step"), (5, "total")},
            (8, "step"): {(11, "step"), (8, "total")},
            (4, "lexval"): {(3, "weight")}, (7, "lexval"): {(6, "weight")},
            (10, "lexval"): {(9, "weight")},
            (3, "weight"): {(2, "total")}, (6, "weight"): {(5, "total")},
            (9, "weight"): {(8, "total")}, (11, "total"): {(8, "total")},
            (8, "total"): {(5, "total")}, (5, "total"): {(2, "total")},
            (2, "total"): {(0, "total")},
        })
        order = evaluate(graph)
        position = {vertex: index for index, vertex in enumerate(order)}
        self.assertEqual(set(order), set(graph.edges))
        for source, targets in graph.edges.items():
            for target in targets:
                self.assertLess(position[source], position[target])
        self.assertEqual([node.attributes for node in graph.nodes], [
            {"total": 8}, {"lexval": "+"}, {"step": 1, "total": 8},
            {"weight": 1}, {"lexval": "x"}, {"step": 2, "total": 7},
            {"weight": 2}, {"lexval": "y"}, {"step": 3, "total": 3},
            {"weight": 1}, {"lexval": "x"}, {"step": 4, "total": 0},
        ])
        self.assertEqual(graph.nodes[11].production, Production("L", ()))
        self.assertEqual(graph.nodes[11].children, [])

    def test_temporarily_circular_rule_reports_and_stops(self):
        rules = RULES.copy()
        production = Production("S", ("+", "L"))
        rules[production] = (
            Rule((2, "step"), ((2, "total"),), lambda total: total),
            rules[production][1],
        )
        tree = build_tree(GRAMMAR, self.table, "+x")
        with self.assertRaisesRegex(CircularSDD, r"^SDD is circular\.$"):
            evaluate(dependency_graph(tree, rules))
        self.assertEqual(tree.attributes, {})
        output = StringIO()
        with redirect_stdout(output):
            run_sdd(["+x", "-"], rules)
        self.assertEqual(output.getvalue(), "SDD is circular.\n")

    def test_sdd_cli_output_and_batch_boundary(self):
        result = subprocess.run(
            [sys.executable, "-B", str(Path(__file__).resolve().parents[1] / "main.py"), "--sdd"],
            input="+\n?\n\n+xyx\n", text=True, capture_output=True, check=True,
        )
        self.assertEqual(result.stderr, "")
        self.assertEqual(result.stdout, (
            "S[0] total=0\n  +[1] lexval='+'\n  L[2] step=1, total=0\n"
            "Evaluation order: 2.step -> 1.lexval -> 2.total -> 0.total\n"
            "S.total = 0\nno\n"
        ))
