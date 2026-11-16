"""The public sets, each loaded from its authors' repository and turned into one item shape:

    {"id", "dataset", "type": noul|tfu|choice|score, "state", "question": {"instructions", "criteria"?},
     "keys": the answer keys in order, "expected": the right key, "tier"?}

noul answers are "yes" / "no"; tfu answers are "true" / "false" / "unknown"; choice answers are the option keys; score answers are "0", "1", ...
A set is downloaded once into the Hub cache (revision pinned below); nothing is written into the sets.
"""
from __future__ import annotations

import json
from pathlib import Path

DATASETS = {
    "opendecisions": {"repo": "jgeuter/OpenDecisions", "note": "2352 decisions, JevBench v1.6 composition, evaluation only"},
    "jeval": {"repo": "carlosxiang/JEVal", "note": "11257 examples from 36 public datasets (choice / noul / score)"},
    "typed-decision-bench": {"repo": "SamuelChien821/typed-decision-bench", "note": "5028 states with 1-10 typed questions each, 21 public datasets"},
    "decision-questions": {"repo": "mihailgribov/decision-questions", "note": "3358 questions: noul / tfu / choice / score"},
}


def _get(repo: str, name: str) -> Path:
    from huggingface_hub import hf_hub_download
    return Path(hf_hub_download(repo, name, repo_type="dataset"))


def _lines(p: Path):
    with open(p, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                yield json.loads(line)


def opendecisions(limit: int = 0) -> list[dict]:
    out = []
    for r in _lines(_get(DATASETS["opendecisions"]["repo"], "opendecisions.jsonl")):
        q = r["question"]
        out.append({"id": r["id"], "dataset": "opendecisions", "type": q["type"], "state": r["state"],
                    "question": {"instructions": q["instructions"], "criteria": q.get("criteria")},
                    "keys": ["yes", "no"] if q["type"] == "noul" else list(r["labels"]), "expected": str(r["expected"]),
                    "tier": r.get("tier"), "raw": r})
    return out[:limit] if limit else out


def jeval(limit: int = 0) -> list[dict]:
    import pyarrow.parquet as pq
    out = []
    for r in pq.read_table(_get(DATASETS["jeval"]["repo"], "data/test.parquet")).to_pylist():
        (qk, q), = json.loads(r["questions_json"]).items()
        label = json.loads(r["label_json"])
        t = q["type"]
        if t == "noul":
            keys, exp = ["yes", "no"], ("yes" if int(label) == 1 else "no")          # label 1 = the true side
        elif t == "score":
            keys, exp = [str(i) for i in range(len(q["criteria"]))], str(int(label))
        else:
            keys, exp = list(q["criteria"]), str(label)
        out.append({"id": r["id"], "dataset": "jeval", "type": t, "state": r["state"], "source": r["source"],
                    "question": {"instructions": q["instructions"], "criteria": q.get("criteria")}, "keys": keys, "expected": exp})
    return out[:limit] if limit else out


def typed_decision_bench(limit: int = 0) -> list[dict]:
    out = []
    for suite in ("data-and-operations", "real-time-and-agents", "retrieval-and-knowledge", "safety-and-quality", "workflow-control"):
        for r in _lines(_get(DATASETS["typed-decision-bench"]["repo"], f"bench/suites/{suite}/items.jsonl")):
            if not r.get("questions"):                                                # 359 items carry no question body in the public file
                continue
            for qk, q in r["questions"].items():
                if qk not in (r.get("gold") or {}):                                      # a question without a published answer cannot be scored
                    continue
                g, t = r["gold"][qk], q["type"]
                if t == "noul":
                    keys, exp = ["yes", "no"], ("yes" if int(g) == 1 else "no")
                elif t == "score":
                    keys, exp = [str(i) for i in range(len(q["criteria"]))], str(int(g))
                else:
                    keys, exp = list(q["criteria"]), str(g)
                out.append({"id": f"{r['id']}::{qk}", "dataset": "typed-decision-bench", "type": t, "state": r["state"], "suite": suite,
                            "question": {"instructions": q["instructions"], "criteria": q.get("criteria")}, "keys": keys, "expected": exp})
    return out[:limit] if limit else out


def decision_questions(limit: int = 0) -> list[dict]:
    out = []
    for r in _lines(_get(DATASETS["decision-questions"]["repo"], "data/test.jsonl")):
        q = dict(r["question"])
        crit = json.loads(q["criteria"]) if isinstance(q.get("criteria"), str) else q.get("criteria")
        t, ans = r["type"], str(r["answer"])
        if t in ("noul", "tfu") and isinstance(crit, dict):
            crit = {k: v for k, v in crit.items() if k != "unknown"}                 # the third answer is read without being asked for
        keys = {"noul": ["yes", "no"], "tfu": ["true", "false", "unknown"]}.get(t) or ([str(i) for i in range(len(crit))] if t == "score" else list(crit))
        out.append({"id": r["id"], "dataset": "decision-questions", "type": t, "state": r["state"], "category": r.get("category"),
                    "question": {"instructions": q["instructions"], "criteria": crit}, "keys": keys, "expected": ans})
    return out[:limit] if limit else out


LOADERS = {"opendecisions": opendecisions, "jeval": jeval, "typed-decision-bench": typed_decision_bench, "decision-questions": decision_questions}


# ---- sets without a third answer: loaded from the Hub (or the authors' GitHub repository at a pinned commit) and drawn with a fixed seed ----
EXTERNAL = {
    "boolq": {"repo": "google/boolq", "note": "BoolQ, validation, yes/no (CC BY-SA 3.0); at most 3000 questions drawn with seed 0"},
    "arc": {"repo": "allenai/ai2_arc", "note": "ARC-Challenge, test, multiple choice (CC BY-SA 4.0)"},
    "helpsteer": {"repo": "nvidia/HelpSteer", "note": "HelpSteer, validation, helpfulness 0-4 (CC BY 4.0)"},
    "jevbench": {"repo": "fstandhartinger/jevbench", "note": "JevBench public items (easy, original, hard tiers), pinned commit"},
}
DATASETS.update(EXTERNAL)
SEED, CAP = 0, 3000
JEVBENCH_COMMIT = "2fa63fa3226cb369795525ed011800f57dcbd894"
JEVBENCH_URL = "https://raw.githubusercontent.com/fstandhartinger/jevbench/" + JEVBENCH_COMMIT + "/datasets/public/{}.jsonl"


def _draw(rows: list[dict], cap: int = CAP) -> list[dict]:
    import random
    rows = list(rows); random.Random(SEED).shuffle(rows)
    return rows[:cap]


def boolq(limit: int = 0) -> list[dict]:
    from datasets import load_dataset
    d = load_dataset(EXTERNAL["boolq"]["repo"], split="validation")
    rows = [{"id": f"boolq-{i}", "dataset": "boolq", "type": "noul", "state": x["passage"],
             "question": {"instructions": x["question"].strip().capitalize() + "?", "criteria": {"true": "the answer is yes", "false": "the answer is no"}},
             "keys": ["yes", "no"], "expected": "yes" if x["answer"] else "no"} for i, x in enumerate(d)]
    return _draw(rows)[:limit] if limit else _draw(rows)


def arc(limit: int = 0) -> list[dict]:
    from datasets import load_dataset
    d = load_dataset(EXTERNAL["arc"]["repo"], "ARC-Challenge", split="test"); rows = []
    for x in d:
        ks = x["choices"]["label"]
        rows.append({"id": "arc-" + x["id"], "dataset": "arc", "type": "choice", "state": x["question"],
                     "question": {"instructions": "Choose the correct answer.", "criteria": {f"option_{k}": t for k, t in zip(ks, x["choices"]["text"])}},
                     "keys": [f"option_{k}" for k in ks], "expected": "option_" + x["answerKey"]})
    rows = _draw(rows)
    return rows[:limit] if limit else rows


def helpsteer(limit: int = 0) -> list[dict]:
    from datasets import load_dataset
    d = load_dataset(EXTERNAL["helpsteer"]["repo"], split="validation")
    levels = ["Not helpful at all", "Barely helpful", "Somewhat helpful", "Mostly helpful", "Extremely helpful"]
    rows = [{"id": f"helpsteer-{i}", "dataset": "helpsteer", "type": "score", "state": "Request: " + x["prompt"] + "\nResponse: " + x["response"],
             "question": {"instructions": "Rate how helpful the response is to the request.", "criteria": levels},
             "keys": [str(k) for k in range(5)], "expected": str(x["helpfulness"])} for i, x in enumerate(d)]
    rows = _draw(rows)
    return rows[:limit] if limit else rows


def jevbench(limit: int = 0) -> list[dict]:
    import urllib.request
    cache = Path.home() / ".cache" / "inola-evals" / "jevbench" / JEVBENCH_COMMIT; cache.mkdir(parents=True, exist_ok=True)
    rows = []
    for tier in ("easy", "original", "hard"):
        p = cache / f"{tier}.jsonl"
        if not p.exists():
            urllib.request.urlretrieve(JEVBENCH_URL.format(tier), p)
        for r in _lines(p):
            q = r["question"]; t = q["type"]
            state = r["state"] if isinstance(r["state"], str) else json.dumps(r["state"], ensure_ascii=False)
            keys = ["yes", "no"] if t == "noul" else [str(k) for k in r["labels"]]
            rows.append({"id": r["id"], "dataset": "jevbench", "type": t, "state": state, "tier": tier,
                         "question": {"instructions": q["instructions"], "criteria": q.get("criteria")}, "keys": keys, "expected": str(r["expected"])})
    return rows[:limit] if limit else rows


LOADERS.update({"boolq": boolq, "arc": arc, "helpsteer": helpsteer, "jevbench": jevbench})


def load(name: str, limit: int = 0) -> list[dict]:
    """limit > 0: a seeded random sample of that many rows (the same rows on every run)"""
    if name not in LOADERS:
        raise KeyError(f"unknown set {name!r}; known: {', '.join(LOADERS)}")
    rows = LOADERS[name](0)
    if limit and limit < len(rows):
        import random
        rows = random.Random(0).sample(rows, limit)
    return rows
