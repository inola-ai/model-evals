# Inola model evaluations

Evaluations of every Inola model on public benchmarks, kept with every answer so anyone can check the numbers.
One repository for all models: the harness of a benchmark is shared by every model and version measured on it.

## Layout

```
benchmarks/<benchmark>/          harness: dataset loader, runner, scoring — shared by the models of a task
models/<model>/
  README.md                      the model's quality page, built from its results
  results/<benchmark>/<version>/
    answers.jsonl                every answer of the model
    metrics.json                 the numbers on the quality page
    run.json                     the run card: date, model and version, harness commit, how it was called
                                 (public API or weights), hardware
tools/                           builders of the quality pages
```

## Rules

- **A run is never overwritten.** Each model version has its own directory; a re-run is a new run card.
- **Released versions only.** A version that users cannot call is not measured here.
- **Through the public API where possible**, so a run can be repeated with any key.
- **No benchmark data in the repository.** Loaders download it from its authors; the licences are theirs.
- **No code of the models.** Weights, descriptions and request forms live in the model's repository on Hugging Face;
  this repository holds the evidence of quality, and the model card links here.
- History starts with the current versions: earlier measurements are not carried over.

## Models

| model | page |
|---|---|
| Decider | [models/decider](models/decider/) |

## Licence

Apache-2.0 for the code. Benchmark data belongs to its authors and is not stored here.
