"""Runs a model through the public API (POST <api>/v1/infer) over the sets and writes <out>/<set>.jsonl in the same
row shape as the local runner (id, dataset, type, expected, probs) - resumable, Ctrl-C stops cleanly.

A tfu question is asked as a choice of three (true / false / unknown): the API has no tfu type, and a model without a
third answer reads "unknown" as an option like any other.
"""
from __future__ import annotations

import json
import os
import signal
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from . import datasets

UNKNOWN = "the text does not say: it cannot be decided from the text"


def question(it: dict) -> dict:
    q = {"type": it["type"], "instructions": it["question"]["instructions"]}
    crit = it["question"].get("criteria")
    if it["type"] == "tfu":
        crit = dict(crit or {"true": "true", "false": "false"}); crit["unknown"] = UNKNOWN
        q["type"] = "choice"
    if crit is not None:
        q["criteria"] = crit
    return q


def probs_of(it: dict, a: dict) -> dict:
    """The API's answer -> probabilities over the item's answer keys."""
    if a["type"] == "noul":
        p = float(a["noul"]); return {"yes": p, "no": 1 - p}
    p = {str(k): float(v) for k, v in a["probabilities"].items()}
    return {k: p.get(k, 0.0) for k in it["keys"]}


def ask(api: str, key: str, model: str, it: dict, tries: int = 5) -> dict:
    body = json.dumps({"model": model, "input": {"state": it["state"], "questions": {"q": question(it)}}}).encode()
    for n in range(tries):
        req = urllib.request.Request(api.rstrip("/") + "/v1/infer", data=body, method="POST",
                                     headers={"Content-Type": "application/json", "Authorization": "Bearer " + key})
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503, 504) and n + 1 < tries:
                time.sleep(2 ** n); continue
            return {"error": f"HTTP {e.code}: {e.read()[:200].decode(errors='replace')}"}
        except (urllib.error.URLError, TimeoutError) as e:
            if n + 1 < tries:
                time.sleep(2 ** n); continue
            return {"error": str(e)[:200]}
    return {"error": "no answer"}


def run(api: str, key_env: str, model: str, names: list[str], out: Path, limit: int = 0, threads: int = 8) -> dict:
    """Returns {"versions": the model versions that answered} for the run card."""
    key = os.environ.get(key_env, "")
    if not key:
        sys.exit(f"{key_env} is not set: the API key goes in the environment")
    out.mkdir(parents=True, exist_ok=True)
    stop = {"v": False}
    signal.signal(signal.SIGINT, lambda *_: stop.__setitem__("v", True)); signal.signal(signal.SIGTERM, lambda *_: stop.__setitem__("v", True))
    versions: set[str] = set()
    for name in names:
        items = datasets.load(name, limit); path = out / f"{name}.jsonl"
        done = {json.loads(l)["id"] for l in open(path)} if path.exists() else set()
        todo = [it for it in items if it["id"] not in done]
        print(f"== {name}: {len(done)}/{len(items)} done, {len(todo)} to run", flush=True)
        t0, n, errs = time.time(), len(done), 0
        with open(path, "a", encoding="utf-8") as f, ThreadPoolExecutor(threads) as pool:
            for i in range(0, len(todo), 50):
                chunk = todo[i:i + 50]
                for it, res in zip(chunk, pool.map(lambda it: ask(api, key, model, it), chunk)):
                    rec = {"id": it["id"], "dataset": name, "type": it["type"], "expected": it["expected"]}
                    if "error" in res:
                        rec["probs"], rec["error"] = {}, res["error"]; errs += 1
                    else:
                        versions.add(res.get("version", "?"))
                        rec["probs"] = probs_of(it, res["output"]["answers"]["q"]); rec["version"] = res.get("version")
                    f.write(json.dumps(rec, ensure_ascii=False) + "\n")
                f.flush(); n += len(chunk)
                print(f"  {name} {n}/{len(items)}  errors {errs}  {time.time() - t0:.0f}s", flush=True)
                if stop["v"]:
                    sys.exit(f"stopped at {name} {n}/{len(items)}; continue: the same command")
        print(f"== {name}: finished, errors {errs}", flush=True)
    return {"versions": sorted(versions)}
