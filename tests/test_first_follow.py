from io import StringIO
from pathlib import Path
import subprocess
import sys
import unittest

from first_follow import compute_first, compute_follow, first_of_sequence
from grammar import Production, read_grammar


class GrammarTests(unittest.TestCase):
    def test_start_and_ordered_productions(self):
        stream = StringIO("3\nB -> bBc e\nA -> aA d\nS -> AB\nd\n")
        grammar = read_grammar(stream)
        self.assertEqual(grammar.start, "S")
        self.assertEqual(grammar.nonterminals, {"A", "B", "S"})
        self.assertEqual(grammar.terminals, {"a", "b", "c", "d"})
        self.assertEqual(grammar.productions, (
            Production("B", ("b", "B", "c")), Production("B", ()),
            Production("A", ("a", "A")), Production("A", ("d",)),
            Production("S", ("A", "B")),
        ))
        self.assertEqual(stream.readline(), "d\n")

    def test_reserved_symbols_and_invalid_heads(self):
        for source in (
            "1\nS -> ae\n", "1\nS -> $\n", "1\nS -> A\n",
            "2\nS -> a\nS -> b\n", "1\nA -> a\n",
        ):
            with self.subTest(source=source), self.assertRaises(ValueError):
                read_grammar(StringIO(source))


class FirstFollowTests(unittest.TestCase):
    def sets(self, source):
        grammar = read_grammar(StringIO(source))
        first = compute_first(grammar)
        follow = compute_follow(grammar, first)
        self.assertTrue(all("e" not in symbols for symbols in follow.values()))
        return first, follow

    def test_without_epsilon_and_with_direct_recursion(self):
        first, follow = self.sets("2\nA -> Aa b\nS -> A!\n")
        self.assertEqual(first, {
            "A": {"b"}, "S": {"b"}, "a": {"a"}, "b": {"b"}, "!": {"!"},
        })
        self.assertEqual(follow, {"A": {"a", "!"}, "S": {"$"}})

    def test_one_epsilon_production(self):
        first, follow = self.sets("3\nS -> AB\nA -> aA d\nB -> bBc e\n")
        self.assertEqual(first["S"], {"a", "d"})
        self.assertEqual(first["B"], {"b", "e"})
        self.assertEqual(follow, {"A": {"b", "$"}, "B": {"c", "$"}, "S": {"$"}})

    def test_nullable_sequences_and_follow(self):
        first, follow = self.sets("4\nS -> ABC\nA -> a e\nB -> b e\nC -> c e\n")
        self.assertEqual(first["S"], {"a", "b", "c", "e"})
        self.assertEqual(first_of_sequence("ABC", first), {"a", "b", "c", "e"})
        self.assertEqual(first_of_sequence("ABcA", first), {"a", "b", "c"})
        self.assertEqual(first_of_sequence((), first), {"e"})
        self.assertEqual(follow, {
            "A": {"b", "c", "$"}, "B": {"c", "$"}, "C": {"$"}, "S": {"$"},
        })

    def test_indirect_recursion_and_follow_fixed_point(self):
        first, follow = self.sets("4\nA -> B\nB -> A C\nC -> 1\nS -> A?\n")
        self.assertEqual(first, {
            "A": {"1"}, "B": {"1"}, "C": {"1"}, "S": {"1"},
            "1": {"1"}, "?": {"?"},
        })
        self.assertEqual(follow, {"A": {"?"}, "B": {"?"}, "C": {"?"}, "S": {"$"}})


PROMPT = "Select a parser (T: for LL(1), B: for SLR(1), Q: quit):\n"


class CommandLineTests(unittest.TestCase):
    def run_main(self, source, *args):
        result = subprocess.run(
            [sys.executable, "-B", str(Path(__file__).resolve().parents[1] / "main.py"), *args],
            input=source, text=True, capture_output=True, check=True,
        )
        self.assertEqual(result.stderr, "")
        return result.stdout

    def test_sets_order_and_spacing(self):
        source = "3\nB -> z ! 2 e\nA -> ? e\nS -> AB\nT\n?z\n\nQ\n"
        self.assertEqual(self.run_main(source, "--sets"), (
            "First(A) = {?, e}\nFirst(B) = {!, 2, z, e}\n"
            "First(S) = {!, 2, ?, z, e}\n"
            "Follow(A) = {!, 2, z, $}\nFollow(B) = {$}\nFollow(S) = {$}\n"
            + PROMPT + "yes\n" + PROMPT
        ))

    def test_empty_follow_set(self):
        self.assertEqual(self.run_main("2\nS -> e\nX -> x\nQ\n", "--sets"), (
            "First(S) = {e}\nFirst(X) = {x}\nFollow(S) = {$}\nFollow(X) = {}\n" + PROMPT
        ))

    def test_without_sets_has_only_official_output(self):
        self.assertEqual(self.run_main("1\nS -> e\nQ\n"), PROMPT)

    def test_official_example_one(self):
        source = "3\nS -> S+T T\nT -> T*F F\nF -> (S) i\ni+i\n(i)\n(i+i)*i)\n\n"
        self.assertEqual(self.run_main(source), "Grammar is SLR(1).\nyes\nyes\nno\n")

    def test_official_example_two_and_parser_switching(self):
        grammar = "3\nS -> AB\nA -> aA d\nB -> bBc e\n"
        batch = "d\nadbc\na\n\n"
        expected = "yes\nyes\nno\n"
        self.assertEqual(self.run_main(grammar + "T\n" + batch + "Q\n"), (
            PROMPT + expected + PROMPT
        ))
        self.assertEqual(self.run_main(grammar + "T\n" + batch + "B\n" + batch + "Q\n"), (
            PROMPT + expected + PROMPT + expected + PROMPT
        ))

    def test_official_example_three(self):
        self.assertEqual(self.run_main("1\nS -> SS a\na\n"),
                         "Grammar is neither LL(1) nor SLR(1).\n")

    def test_ll1_only(self):
        source = "2\nS -> Aa bAb\nA -> e\na\nbb\nb\n\na\n"
        self.assertEqual(self.run_main(source), "Grammar is LL(1).\nyes\nyes\nno\n")

    def test_e_and_empty_batch(self):
        source = "1\nS -> e\nT\ne\n\nB\n\nB\ne\n$\n\nQ\n"
        self.assertEqual(self.run_main(source), (
            PROMPT + "yes\n" + PROMPT + PROMPT + "yes\nno\n" + PROMPT
        ))

    def test_windows_line_endings(self):
        source = "1\r\nS -> a\r\nT\r\na\r\nb\r\n\r\nQ\r\n"
        self.assertEqual(self.run_main(source), PROMPT + "yes\nno\n" + PROMPT)


if __name__ == "__main__":
    unittest.main()
