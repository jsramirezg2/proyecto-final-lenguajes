# Formal Languages and Compilers Final Project

Santiago Villamizar and Juan Sebastián Ramírez

This program computes FIRST and FOLLOW sets, classifies a context-free grammar as LL(1) and/or SLR(1), and recognizes input strings using the applicable parsers. A separate mode evaluates a syntax-directed definition (SDD) on a parse tree.

## Requirements and installation

Run these commands from the project directory with Python 3.10 or later. No packages, build step, or virtual environment are required. The implementation and test suite were verified with Python 3.12.10 on macOS 27.0.1 (build 26A434). The report was generated with ReportLab 4.4.9, which is only a document-authoring tool.

## Run the parsers

```sh
python3 -B main.py
```

Enter the number of nonterminals, followed by one production line for each. The start symbol is `S`. Separate alternatives with spaces, write epsilon as `e`, and omit the reserved end marker `$` from all inputs.

If both parsers apply, enter `T` for LL(1), `B` for SLR(1), or `Q` to quit. If only one parser applies, it starts immediately. Enter one string per line. A line containing only `e` represents the empty string. An empty line ends the batch.

```sh
printf '3\nS -> AB\nA -> aA d\nB -> bBc e\nT\nd\nadbc\na\n\nQ\n' | python3 -B main.py
```

Use `--sets` to print FIRST and FOLLOW before classification and parsing.

```sh
printf '2\nS -> AA\nA -> aA b\nB\nabb\n\nQ\n' | python3 -B main.py --sets
```

## Run the SDD evaluator

```sh
printf '+xyx\n-yx\n+\n+xz\n\n' | python3 -B main.py --sdd
```

The built-in grammar accepts a sign followed by zero or more `x` and `y` characters. The evaluator computes the signed, one-based positional sum with weights 1 for `x` and 2 for `y`. For valid input it prints the annotated tree, a topological evaluation order, and `S.total`. For invalid input it prints `no`. An empty line ends the batch.

## Tests

```sh
python3 -B -m unittest discover -s tests -v
```

The suite covers the official examples, all four grammar classifications, LR(0) states and conflicts, and SDD evaluation and circularity.

## Files

| File | Purpose |
| --- | --- |
| `grammar.py` | Grammar and production representation and input |
| `first_follow.py` | Fixed-point FIRST and FOLLOW computations |
| `ll1.py` | Predictive table, LL(1) conflicts, and stack parser |
| `slr.py` | LR(0) collection, SLR tables and conflicts, and state-stack parser |
| `sdd.py` | Parse tree, dependency graph, and topological evaluation |
| `sdd_example.py` | Example grammar, semantic rules, and main attribute |
| `main.py` | Terminal interface for both modes |
| `tests/` | Standard-library test suite |
| `report.pdf` | Technical report with worked examples and test results |

## Generative AI use

OpenAI Codex helped review the assignment and book sections, plan the project, write and verify the implementation and tests, and draft and generate this README and the report. The worked examples in the report were checked against the running program. Each group member is responsible for reading the assigned sections, independently working through the required examples, and explaining the code and calculations during the defense.
