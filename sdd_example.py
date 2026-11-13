from io import StringIO

from grammar import Production, read_grammar
from sdd import Rule

GRAMMAR = read_grammar(StringIO("3\nS -> +L -L\nL -> DL e\nD -> x y\n"))
MAIN_ATTRIBUTE = "total"


def signed_start(sign):
    return (
        Rule((2, "step"), (), lambda: sign),
        Rule((0, "total"), ((2, "total"),), lambda total: total),
    )


WEIGHT_RULE = Rule((0, "weight"), ((1, "lexval"),), lambda lexval: {"x": 1, "y": 2}[lexval])

RULES = {
    Production("S", ("+", "L")): signed_start(1),
    Production("S", ("-", "L")): signed_start(-1),
    Production("L", ("D", "L")): (
        Rule((2, "step"), ((0, "step"),), lambda step: step + (1 if step > 0 else -1)),
        Rule((0, "total"), ((0, "step"), (1, "weight"), (2, "total")),
             lambda step, weight, tail: step * weight + tail),
    ),
    Production("L", ()): (Rule((0, "total"), (), lambda: 0),),
    Production("D", ("x",)): (WEIGHT_RULE,),
    Production("D", ("y",)): (WEIGHT_RULE,),
}
