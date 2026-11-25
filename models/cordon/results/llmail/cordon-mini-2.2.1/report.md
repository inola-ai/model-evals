| Defense | | Phase 1 | Phase 2 |
|---|---|---:|---:|
| Prompt Shield v1 | Azure text classifier | 60.4% | 42.5% |
| Prompt Shield v2 | Azure text classifier | 67.8% | 48.7% |
| TaskTracker, Phi-3 14B | probe on LLM activations | 76.1% | 89.6% |
| TaskTracker, Phi-4 14B | probe on LLM activations | 88.1% | 99.8% |
| TaskTracker, Phi-3.5-MoE | probe on LLM activations | 94.9% | 99.1% |
| LLM Judge | LLM prompted to judge | 99.4% | 96.5% |
| **Inola Cordon mini 2.2.1** | measured with model-evals | **99.99%** ± 0.0 | **100.0%** ± 0.1 |

- Threshold: score > 0.00010, the lowest that leaves every benign email quiet; benign emails flagged: 0 of 203 (0 not judged).
- Attacks caught: 21,392 of 21,394 (Phase 1) and 3,165 of 3,165 (Phase 2); not judged by the detector, counted as misses: 0 and 0; not scored yet: 0.
- Detector version: 2.2.1.
- ± is the half-width of the 95% Wilson interval. Paper rows: Table 3 of arXiv:2506.09956.

At the service's own operating point (its verdict, not the paper's rule): Phase 1 71.6% ± 0.6, Phase 2 83.3% ± 1.3, benign emails flagged 0 of 203.
