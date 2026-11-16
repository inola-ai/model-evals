# Decider

Quality page of the decision models (Decider and its open version), built from `results/`.

## Benchmarks

The harness is `benchmarks/decision_sets`: every set is loaded from its authors' repository, nothing is copied here.

| set | source | what it is |
|---|---|---|
| `decision-questions` | [mihailgribov/decision-questions](https://huggingface.co/datasets/mihailgribov/decision-questions) | ours: yes-no, choice, score (3358 questions; those with a third answer are not scored) |
| `jevbench` | [fstandhartinger/jevbench](https://github.com/fstandhartinger/jevbench), public items, pinned commit | 231 public decision tasks of JevBench |
| `boolq` | [google/boolq](https://huggingface.co/datasets/google/boolq) | yes-no reading questions, at most 3000 drawn with seed 0 |
| `arc` | [allenai/ai2_arc](https://huggingface.co/datasets/allenai/ai2_arc) | ARC-Challenge, multiple choice |
| `helpsteer` | [nvidia/HelpSteer](https://huggingface.co/datasets/nvidia/HelpSteer) | rate the helpfulness of a response, five levels |

The harness also loads `opendecisions`, `jeval` and `typed-decision-bench`; they have not been run for any version yet.
Per question: `id, type, expected, probs, logits`; per set and kind: accuracy ± binomial SE and the NLL of the right answer.
A question that cannot be asked counts as wrong.

## Before a number is published

Each set is checked against the training data of the measured version (by state text, `tools/overlap.py`). The questions that share text are listed in
`excluded_ids.json` next to the answers and are left out of every number; the count is in the last column.

## Results

<!-- results -->

| version | set | kind | questions | accuracy | NLL | left out |
|---|---|---|---|---|---|---|
| inola-decider-open-1.1.0 | ARC-Challenge (test) | `choice` | 1170 | 0.920 ± 0.008 | 0.275 | 2 |
| inola-decider-open-1.1.0 | BoolQ (validation) | `noul` | 2881 | 0.876 ± 0.006 | 0.387 | 119 |
| inola-decider-open-1.1.0 | decision-questions | `choice` | 734 | 0.941 ± 0.009 | 0.177 | 135 |
| inola-decider-open-1.1.0 | decision-questions | `noul` | 1128 | 0.905 ± 0.009 | 0.268 | 128 |
| inola-decider-open-1.1.0 | decision-questions | `score` | 161 | 0.783 ± 0.033 | 0.537 | 115 |
| inola-decider-open-1.1.0 | HelpSteer (validation, helpfulness 0-4) | `score` | 1789 | 0.481 ± 0.012 | 1.264 | 0 |
| inola-decider-open-1.1.0 | JevBench public items | `choice` | 139 | 0.827 ± 0.032 | 0.395 | 0 |
| inola-decider-open-1.1.0 | JevBench public items | `noul` | 74 | 0.919 ± 0.032 | 0.260 | 0 |
| inola-decider-open-1.1.0 | JevBench public items | `score` | 18 | 0.833 ± 0.088 | 0.288 | 0 |

<!-- /results -->

Run a version: `cd benchmarks && python -m decision_sets run --model <release dir or Hub id> --out <dir> --sets jevbench,boolq,arc,helpsteer,decision-questions`.
A run is never overwritten: a new version or a re-run has its own directory and run card.
