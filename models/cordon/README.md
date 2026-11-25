# Cordon

Quality page of the prompt-injection models (Cordon), built from `results/`. The harness is
[`benchmarks/injection`](../../benchmarks/injection/): every set is loaded from its authors, nothing is copied here.

## Cordon mini 2.2.1

Measured 25 November 2026 through the public API (`api.inola.ai`, real time and the Batch API), version 2.2.1 pinned
in every request. Every answer is in `results/<set>/cordon-mini-2.2.1/answers.jsonl`; the run card (`run.json`) says
how each set was called.

### LLMail-Inject (Microsoft) — Table 3 of the paper with one more row

| Defense | | Phase 1 | Phase 2 |
|---|---|---:|---:|
| Prompt Shield v1 | Azure text classifier | 60.4% | 42.5% |
| Prompt Shield v2 | Azure text classifier | 67.8% | 48.7% |
| TaskTracker, Phi-3 14B | probe on LLM activations | 76.1% | 89.6% |
| TaskTracker, Phi-4 14B | probe on LLM activations | 88.1% | 99.8% |
| TaskTracker, Phi-3.5-MoE | probe on LLM activations | 94.9% | 99.1% |
| LLM Judge | LLM prompted to judge | 99.4% | 96.5% |
| **Inola Cordon mini 2.2.1** | measured with model-evals | **99.99%** | **100.0%** ± 0.1 |

21,392 of 21,394 attacks caught in Phase 1 and 3,165 of 3,165 in Phase 2, with none of the 203 benign emails flagged
(the paper's rule: the threshold is the highest benign score, here the lowest score the API returns, 0.0001). With
the threshold far above every benign email, at 0.01, 99.9% are still caught. At the operating points the service
publishes: 99.9% at `fpr_1e-02`, 97.9% at `fpr_1e-03`, and 71.6% / 83.3% at its default verdict (`fpr_1e-04`), each
with no benign email flagged. Microsoft rows: Table 3 of arXiv:2506.09956.
[Report](results/llmail/cordon-mini-2.2.1/report.md).

### Quadrat-IPI v1.0.2 — 79,800 rows, recall at a fixed false-alarm rate

| false-alarm rate | threshold | recall | false alarms of 63,000 | email | document | web page |
|---:|---:|---:|---:|---:|---:|---:|
| 1% | 0.0403 | **99.9%** | 603 | 99.8% | 99.9% | 99.9% |
| 0.1% | 0.750 | **99.3%** | 49 | 98.7% | 99.8% | 99.4% |
| 0.05% and 0.02% | 0.982 | **98.1%** | 10 | 96.7% | 99.5% | 98.3% |

At the service's own verdict, with no threshold set on this data: recall 99.2%, 37 false alarms of 63,000. The two
strictest points coincide because 10 clean rows and 16,488 of the 16,800 injected ones get the highest score the API
returns (0.9999); a point below 10 false alarms cannot be set from these scores. Quadrat-IPI is built by the authors
of the Inola models. [Report](results/quadrat/cordon-mini-2.2.1/report.md).

### NotInject — harmless prompts that sound suspicious

**Over-defense accuracy 94.1%** at the service's verdict (share of prompts with no alarm, mean of the three splits as
PIGuard reports it): one trigger word 100.0%, two 98.2%, three 84.1%. At the looser published points: 86.4%
(`fpr_1e-03`) and 62.2% (`fpr_1e-02`). NotInject's prompts are requests addressed to an assistant; inside a document,
a request that tells the model what to do is what an injection model is built to flag.
[Report](results/notinject/cordon-mini-2.2.1/report.md).

## Before a number is used

- **Training overlap is not checked yet** for these sets against the training data of 2.2.1. Quadrat-IPI is kept out
  of training by rule; whether LLMail-Inject or NotInject texts, or payloads derived from them, are in the training
  data is still to be verified, and the result will be written here.
- Scores come rounded to four decimals; see [Reading the numbers](../../benchmarks/injection/README.md#reading-the-numbers).
