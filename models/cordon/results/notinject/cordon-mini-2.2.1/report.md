**Inola Cordon mini 2.2.1**: over-defense accuracy **94.1%**, the mean over the three splits (PIGuard's figure); higher is better.

| trigger words | prompts | quiet, the service's verdict | not judged |
|---|---:|---:|---:|
| one | 113 | 100.0% ± 1.6 | 0 |
| two | 113 | 98.2% ± 2.9 | 0 |
| three | 113 | 84.1% ± 6.7 | 0 |
| **all** | **339** | **94.1% ± 2.5** | 0 |

The same prompts at each operating point the service publishes (the false-alarm rate it was set for on clean text):

| operating point | one | two | three | mean |
|---|---:|---:|---:|---:|
| fpr_1e-02 | 66.4% | 76.1% | 44.2% | 62.2% |
| fpr_1e-03 | 92.0% | 94.7% | 72.6% | 86.4% |
| fpr_1e-04 | 100.0% | 98.2% | 84.1% | 94.1% |

By category of the prompt:

| category | prompts | quiet |
|---|---:|---:|
| Common Queries | 126 | 98.4% ± 2.6 |
| Multilingual | 84 | 100.0% ± 2.2 |
| Technique Queries | 87 | 86.2% ± 7.3 |
| Virtual Creation | 42 | 85.7% ± 10.6 |

- Detector version: 2.2.1.
- Not judged (too short for the detector), counted as quiet: 0 of 339.
- ± is the half-width of the 95% Wilson interval. Protocol and data: PIGuard (Li et al., ACL 2025), `leolee99/PIGuard` @ `1b5751e8`.
