from io import StringIO
import unittest

from first_follow import compute_first, compute_follow
from grammar import read_grammar
from ll1 import build_ll1_table, parse_ll1


class LL1Tests(unittest.TestCase):
    def build_table(self, source):
        grammar = read_grammar(StringIO(source))
        first = compute_first(grammar)
        follow = compute_follow(grammar, first)
        return grammar, build_ll1_table(grammar, first, follow)

    def test_simple_grammar(self):
        grammar, table = self.build_table("1\nS -> ab c\n")
        self.assertTrue(table.is_ll1)
        for text, expected in (
            ("ab", True), ("c", True), ("ac", False), ("a", False),
            ("abc", False), ("ab$", False), ("e", False),
        ):
            with self.subTest(text=text):
                self.assertEqual(parse_ll1(grammar, table, text), expected)

    def test_example_from_assignment(self):
        grammar, table = self.build_table("3\nS -> AB\nA -> aA d\nB -> bBc e\n")
        self.assertTrue(table.is_ll1)
        self.assertTrue(parse_ll1(grammar, table, "d"))
        self.assertTrue(parse_ll1(grammar, table, "adbc"))
        self.assertFalse(parse_ll1(grammar, table, "a"))

    def test_external_e_and_iterative_recursion(self):
        grammar, table = self.build_table("1\nS -> aS e\n")
        self.assertTrue(parse_ll1(grammar, table, "e"))
        self.assertTrue(parse_ll1(grammar, table, "a" * 2000))
        self.assertFalse(parse_ll1(grammar, table, "ae"))

    def test_first_first_keeps_original_productions(self):
        grammar, table = self.build_table("1\nS -> ab ac\n")
        self.assertFalse(table.is_ll1)
        self.assertEqual(len(table.cells["S", "a"]), 2)
        for actual, original in zip(table.cells["S", "a"], grammar.productions):
            self.assertIs(actual, original)
        conflict, = table.conflicts
        self.assertEqual(conflict.reason, "FIRST/FIRST")
        self.assertEqual(conflict.lookaheads, {"a"})
        self.assertEqual(conflict.productions, grammar.productions)
        with self.assertRaises(ValueError):
            parse_ll1(grammar, table, "ab")

    def test_first_follow(self):
        grammar, table = self.build_table("2\nS -> Aa\nA -> a e\n")
        self.assertFalse(table.is_ll1)
        self.assertEqual(table.cells["A", "a"], list(grammar.productions[1:]))
        conflict, = table.conflicts
        self.assertEqual(conflict.reason, "FIRST/FOLLOW")
        self.assertEqual(conflict.lookaheads, {"a"})

    def test_nullable_pair_even_when_follow_is_empty(self):
        for source, lookaheads in (
            ("3\nS -> A\nA -> B e\nB -> e\n", {"$"}),
            ("3\nS -> a\nA -> B e\nB -> e\n", set()),
        ):
            with self.subTest(source=source):
                _, table = self.build_table(source)
                self.assertFalse(table.is_ll1)
                conflict, = table.conflicts
                self.assertEqual(conflict.reason, "multiple nullable alternatives")
                self.assertEqual(conflict.lookaheads, lookaheads)
                self.assertEqual(len(table.cells.get(("A", "$"), [])), 2 if lookaheads else 0)

    def test_left_recursion(self):
        grammar, table = self.build_table("1\nS -> S+a a\n")
        self.assertFalse(table.is_ll1)
        self.assertEqual(table.cells["S", "a"], list(grammar.productions))

    def test_single_production_reached_via_first_and_follow(self):
        grammar, table = self.build_table("3\nS -> Aa\nA -> B\nB -> a e\n")
        self.assertEqual(table.cells["A", "a"], [grammar.productions[1]])

    def test_manual_trace_and_table(self):
        grammar, table = self.build_table("2\nS -> Ab\nA -> aA e\n")
        start, repeat, empty = grammar.productions
        self.assertEqual(table.cells, {
            ("S", "a"): [start], ("S", "b"): [start],
            ("A", "a"): [repeat], ("A", "b"): [empty],
        })
        steps = []
        self.assertTrue(parse_ll1(grammar, table, "ab", lambda *step: steps.append(step)))
        self.assertEqual(steps, [
            (("$", "S"), "ab$", "S -> Ab"),
            (("$", "b", "A"), "ab$", "A -> aA"),
            (("$", "b", "A", "a"), "ab$", "match a"),
            (("$", "b", "A"), "b$", "A -> e"),
            (("$", "b"), "b$", "match b"),
            (("$",), "$", "match $"),
        ])


if __name__ == "__main__":
    unittest.main()

