# Injection benchmarks

Prompt-injection detection on public sets, through the Inola API: every document is one `POST /v1/infer` request to
an injection model (`input.state` = the document), and its score is the probability of an injection,
`output.answers.injection.noul`. The record of a document keeps that score, the service's own verdict, its verdict at
each published operating point (`verdicts`) and the version that answered.

| set | harness | what it checks | rule |
|---|---|---|---|
| [LLMail-Inject](https://arxiv.org/abs/2506.09956) (Microsoft, 2025) | `llmail_eval` | attack emails that made an AI email assistant call its tool, against 203 benign business emails | Table 3 of the paper: the threshold leaves every benign email quiet; detection rate per phase |
| [NotInject](https://huggingface.co/datasets/leolee99/NotInject) (PIGuard, ACL 2025) | `notinject_eval` | 339 harmless prompts built around words detectors fire on | over-defense accuracy: share of prompts with no alarm, mean of the three splits |
| [Quadrat-IPI](https://huggingface.co/datasets/mihailgribov/quadrat-ipi) v1.0.2 | `quadrat.py` | injections inside emails, documents and web pages, 16,800 injected and 63,000 clean rows | recall at fixed false-alarm rates set on the clean rows |

Quadrat-IPI is built by the authors of the Inola models; the other two sets are third-party.

## Run

Python 3.10+, no dependencies. Key in `INOLA_API_KEY`. From this directory:

```sh
python -m llmail_eval fetch                                       # data/llmail, sha256-checked
python -m notinject_eval fetch                                    # data/notinject
python3 batch.py llmail --out runs/llmail/cordon-mini-2.2.1 --spec inola:cordon-mini@2.2.1
python -m llmail_eval report --out runs/llmail/cordon-mini-2.2.1 --name "Inola Cordon mini 2.2.1"
QUADRAT_DATA=<quadrat-ipi v1.0.2>/data python3 batch.py quadrat --out runs/quadrat/cordon-mini-2.2.1 --spec inola:cordon-mini@2.2.1
QUADRAT_DATA=<...> python3 quadrat.py report --out runs/quadrat/cordon-mini-2.2.1 --name "Inola Cordon mini 2.2.1"
```

`batch.py` sends the documents not yet scored through the Batch API (`POST /v1/files`, `POST /v1/batches`), in files
under the plan's limit on unfinished batch work, one batch at a time, and appends every answer to `scores.jsonl`;
open batches are kept in `batches.json`, so a stopped run continues without sending a document twice. `--online`
scores from the end of the list in real time beside a running batch. Real time alone:
`python -m llmail_eval score --detector inola:cordon-mini@2.2.1 --out ...` (likewise `notinject_eval`, `quadrat.py score`).

A run directory holds one model version: the version is pinned in every request and a run stops on an answer of
another one. A document the service declines (too long, invalid) is recorded as not judged, never as clean. The
reports read `scores.jsonl` alone; in `models/<model>/results/` the same file is kept as `answers.jsonl`.

## Reading the numbers

- The API returns the score rounded to four decimals (0.0001 to 0.9999). Documents that share the lowest or the
  highest value cannot be told apart by a threshold, so the strictest false-alarm points of Quadrat-IPI can coincide
  or be out of reach; the report shows them as they come out.
- LLMail-Inject: the threshold is found on the same 203 benign emails, as in the paper; zero alarms on 203 bounds the
  false-alarm rate only to 0 to about 1.9%. The challenge attackers were adapting to the paper's defenses, not to the
  model added here, and some of those defenses also see the user's request, while this model sees the email alone.

Tests: `python -m unittest discover tests` (made-up answers, no network).

Data: LLMail-Inject is MIT (`microsoft/llmail-inject-challenge`); NotInject is from `leolee99/PIGuard`; Quadrat-IPI is
on Hugging Face. None of it is stored here.
