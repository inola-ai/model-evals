# Decider

Quality page of the decision models (Decider and its open version), built from `results/`. No results yet.

## Benchmarks

Four public sets of typed decision questions. The harness comes from the open model's benchmark runner
(`inola-ai/decision-open`, `src/decision_open/bench`) and moves to `benchmarks/` here.

| set | source | rows | what it is |
|---|---|---|---|
| `opendecisions` | [jgeuter/OpenDecisions](https://huggingface.co/datasets/jgeuter/OpenDecisions) | 2352 | JevBench v1.6 composition, evaluation only; also scored with its own Capability scorer (MIT) |
| `jeval` | [carlosxiang/JEVal](https://huggingface.co/datasets/carlosxiang/JEVal) | 11257 | 36 public datasets, 10 domains (choice / yes-no / score) |
| `typed-decision-bench` | [SamuelChien821/typed-decision-bench](https://huggingface.co/datasets/SamuelChien821/typed-decision-bench) | 10255 questions | 21 public datasets, 1–10 typed questions per state |
| `decision-questions` | [mihailgribov/decision-questions](https://huggingface.co/datasets/mihailgribov/decision-questions) | 3358 | ours: yes-no, true-false-unsure, choice, score |

Per question: `id, type, expected, probs, logits`; per set and type: accuracy ± binomial SE, NLL of the right answer,
top-probability ECE. A question that cannot be asked counts as wrong.

## Before a number is published

These sets are built from public datasets that a training mix may also contain: each set is checked against the
training data of the measured version (by id and by state text) and the overlap is reported next to the number.
