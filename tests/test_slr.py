from io import StringIO
import unittest

from first_follow import compute_first, compute_follow
from grammar import Production, read_grammar
from slr import Action, Item, build_slr_table, closure, goto, parse_slr


def build(source):
    grammar = read_grammar(StringIO(source))
    return grammar, build_slr_table(grammar, compute_follow(grammar, compute_first(grammar)))


class SLRTests(unittest.TestCase):
    def test_closure_goto_and_canonical_collection(self):
        grammar, table = build("2\nS -> AA\nA -> aA b\n")
        start, repeat, base = grammar.productions
        augmented = Production("S'", ("S",))
        productions = (augmented,) + grammar.productions
        initial = frozenset(map(Item, productions))
        self.assertEqual(closure([Item(augmented)], productions), initial)
        self.assertEqual(goto(initial, "S", productions), {Item(augmented, 1)})
        self.assertEqual(goto(initial, "$", productions), set())
        self.assertEqual(table.states, [
            initial, {Item(start, 1), Item(repeat), Item(base)}, {Item(augmented, 1)},
            {Item(repeat, 1), Item(repeat), Item(base)}, {Item(base, 1)},
            {Item(start, 2)}, {Item(repeat, 2)},
        ])
        self.assertEqual(table.transitions, {
            (0, "A"): 1, (0, "S"): 2, (0, "a"): 3, (0, "b"): 4,
            (1, "A"): 5, (1, "a"): 3, (1, "b"): 4,
            (3, "A"): 6, (3, "a"): 3, (3, "b"): 4,
        })

    def test_manual_action_goto_and_trace(self):
        grammar, table = build("2\nS -> AA\nA -> aA b\n")
        start, repeat, base = grammar.productions
        expected_actions = {
            (state, terminal): {Action("shift", target)}
            for state in (0, 1, 3) for terminal, target in (("a", 3), ("b", 4))
        }
        for state, production in ((4, base), (6, repeat)):
            for terminal in ("a", "b", "$"):
                expected_actions[state, terminal] = {Action("reduce", production)}
        expected_actions[5, "$"] = {Action("reduce", start)}
        expected_actions[2, "$"] = {Action("accept")}
        self.assertEqual(table.action, expected_actions)
        self.assertEqual(table.goto, {(0, "A"): 1, (0, "S"): 2, (1, "A"): 5, (3, "A"): 6})

        trace = []
        self.assertTrue(parse_slr(grammar, table, "abb", lambda *step: trace.append(step)))
        self.assertEqual(trace, [
            ((0,), "abb$", Action("shift", 3)),
            ((0, 3), "bb$", Action("shift", 4)),
            ((0, 3, 4), "b$", Action("reduce", base)),
            ((0, 3, 6), "b$", Action("reduce", repeat)),
            ((0, 1), "b$", Action("shift", 4)),
            ((0, 1, 4), "$", Action("reduce", base)),
            ((0, 1, 5), "$", Action("reduce", start)),
            ((0, 2), "$", Action("accept")),
        ])
        for text in ("ab", "abbb", "abb$", "e"):
            self.assertFalse(parse_slr(grammar, table, text))

    def test_epsilon_reduction_without_popping(self):
        grammar, table = build("1\nS -> aS e\n")
        self.assertTrue(parse_slr(grammar, table, "e"))
        self.assertTrue(parse_slr(grammar, table, "a" * 2000))
        self.assertFalse(parse_slr(grammar, table, "b"))

    def test_shift_reduce_conflict(self):
        grammar, table = build("1\nS -> SS a\n")
        self.assertFalse(table.is_slr1)
        actions, = table.conflicts.values()
        self.assertEqual({action.kind for action in actions}, {"shift", "reduce"})
        with self.assertRaises(ValueError):
            parse_slr(grammar, table, "a")

    def test_reduce_reduce_conflict(self):
        _, table = build("3\nS -> A B\nA -> a\nB -> a\n")
        self.assertFalse(table.is_slr1)
        actions, = table.conflicts.values()
        self.assertEqual(actions, {
            Action("reduce", Production("A", ("a",))),
            Action("reduce", Production("B", ("a",))),
        })
