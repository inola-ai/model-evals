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

Per question: `id, type, expected, probs, logits` (`logits` only for a run on the weights: the public API returns probabilities alone); per set and kind: accuracy ± binomial SE (one SE, not a 95% interval), the NLL of the right answer and the ECE of the confidence in the most probable answer (10 equal-width bins). The probabilities are the calibrated ones the model ships with.
A question that cannot be asked counts as wrong.

## Before a number is published

Each set is checked against the training data of the measured version (by state text, `tools/overlap.py`). The check is exact: two runs of at least 30 plain characters of each state are searched verbatim, so paraphrases and near-duplicates are not found. The questions that share text are listed in
`excluded_ids.json` next to the answers and are left out of every number; the count is in the last column.

## Results

<!-- results -->

| version | set | kind | questions | accuracy ± SE | NLL | ECE | left out |
|---|---|---|---|---|---|---|---|
| inola-decider-mini-1.3.0 | ARC-Challenge (test) | `choice` | 1169 | 0.926 ± 0.008 | 0.233 | 0.014 | 3 |
| inola-decider-open-1.1.0 | ARC-Challenge (test) | `choice` | 1170 | 0.920 ± 0.008 | 0.275 | 0.034 | 2 |
| inola-decider-mini-1.3.0 | BoolQ (validation) | `noul` | 2884 | 0.877 ± 0.006 | 0.308 | 0.030 | 116 |
| inola-decider-open-1.1.0 | BoolQ (validation) | `noul` | 2881 | 0.876 ± 0.006 | 0.387 | 0.074 | 119 |
| inola-decider-mini-1.3.0 | decision-questions | `choice` | 754 | 0.935 ± 0.009 | 0.172 | 0.027 | 115 |
| inola-decider-mini-1.3.0 | decision-questions | `noul` | 1152 | 0.909 ± 0.009 | 0.221 | 0.017 | 104 |
| inola-decider-mini-1.3.0 | decision-questions | `score` | 190 | 0.774 ± 0.030 | 0.548 | 0.070 | 86 |
| inola-decider-open-1.1.0 | decision-questions | `choice` | 734 | 0.941 ± 0.009 | 0.177 | 0.028 | 135 |
| inola-decider-open-1.1.0 | decision-questions | `noul` | 1128 | 0.905 ± 0.009 | 0.268 | 0.047 | 128 |
| inola-decider-open-1.1.0 | decision-questions | `score` | 161 | 0.783 ± 0.033 | 0.537 | 0.053 | 115 |
| inola-decider-mini-1.3.0 | HelpSteer (validation, helpfulness 0-4) | `score` | 1789 | 0.415 ± 0.012 | 1.296 | 0.123 | 0 |
| inola-decider-open-1.1.0 | HelpSteer (validation, helpfulness 0-4) | `score` | 1789 | 0.481 ± 0.012 | 1.264 | 0.072 | 0 |
| inola-decider-mini-1.3.0 | JevBench public items | `choice` | 139 | 0.871 ± 0.029 | 0.332 | 0.045 | 0 |
| inola-decider-mini-1.3.0 | JevBench public items | `noul` | 74 | 0.905 ± 0.034 | 0.288 | 0.030 | 0 |
| inola-decider-mini-1.3.0 | JevBench public items | `score` | 18 | 0.833 ± 0.088 | 0.371 | 0.182 | 0 |
| inola-decider-open-1.1.0 | JevBench public items | `choice` | 139 | 0.827 ± 0.032 | 0.395 | 0.082 | 0 |
| inola-decider-open-1.1.0 | JevBench public items | `noul` | 74 | 0.919 ± 0.032 | 0.260 | 0.039 | 0 |
| inola-decider-open-1.1.0 | JevBench public items | `score` | 18 | 0.833 ± 0.088 | 0.288 | 0.124 | 0 |

<!-- /results -->

Run a version: `cd benchmarks && python -m decision_sets run --model <release dir or Hub id> --out <dir> --sets jevbench,boolq,arc,helpsteer,decision-questions`.
A model served by the API: `python -m decision_sets run --api https://api.inola.tech --model decider-mini --out <dir> --sets ...` (key in `INOLA_API_KEY`). Through the API a question with a third answer is asked as a choice of three; it is still not scored.
A run is never overwritten: a new version or a re-run has its own directory and run card.
