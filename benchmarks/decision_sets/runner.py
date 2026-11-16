"""Runs a model over the sets and writes <out>/<set>.jsonl (one line per question: id, type, expected, probs) - resumable, Ctrl-C stops cleanly."""
from __future__ import annotations

import json
import signal
import sys
import time
from pathlib import Path

from . import datasets


def answer_batch(reader, asks: list[tuple], token_budget: int = 9600, max_rows: int = 32) -> list:
    """[(state, question)] -> [answer body | Exception]: prompts from the package, rows sorted by length and read in right-padded batches by `Reader.read_rows`."""
    out, prep = [None] * len(asks), []
    for i, (state, q) in enumerate(asks):
        try:
            text, keys, marks, legend = reader.prepare(state, q)
            ids = reader.tok(text, add_special_tokens=False)["input_ids"]
            if marks is not None and not all(reader.has_mark(m) for m in marks):
                raise ValueError("a mark of this question has no row in the head")
            prep.append((i, ids, keys, marks, legend, reader.kind_of(q)))
        except (ValueError, KeyError, TypeError) as e:
            out[i] = e
    prep.sort(key=lambda p: len(p[1]))
    cur, width = [], 0
    def flush(cur):
        for (i, _ids, keys, marks, legend, kind), z in zip(cur, reader.read_rows([c[1] for c in cur], [c[3] for c in cur])):
            lg = dict(zip(keys, z)); body = reader.read(kind, lg, legend, marks); body["logits"] = lg; out[i] = body
    for p in prep:
        w = len(p[1])
        if cur and ((len(cur) + 1) * max(width, w) > token_budget or len(cur) >= max_rows):
            flush(cur); cur, width = [], 0
        cur.append(p); width = max(width, w)
    if cur: flush(cur)
    return out


def probs_of(item: dict, body: dict) -> dict:
    """The answer body of the reader -> probabilities over the item's answer keys."""
    t = item["type"]
    if t == "noul":
        p = float(body["noul"]); return {"yes": p, "no": 1 - p}
    p = body["probabilities"]
    if t == "tfu":
        return {"true": p["true"], "false": p["false"], "unknown": p["unsure"]}
    return {k: p[k] for k in item["keys"]}


def run(reader, names: list[str], out: Path, limit: int = 0, batch: int = 64) -> None:
    out.mkdir(parents=True, exist_ok=True)
    stop = {"v": False}
    signal.signal(signal.SIGINT, lambda *_: stop.__setitem__("v", True)); signal.signal(signal.SIGTERM, lambda *_: stop.__setitem__("v", True))
    for name in names:
        items = datasets.load(name, limit); path = out / f"{name}.jsonl"
        done = {json.loads(l)["id"] for l in open(path)} if path.exists() else set()
        todo = [it for it in items if it["id"] not in done]
        print(f"== {name}: {len(done)}/{len(items)} done, {len(todo)} to run", flush=True)
        t0, n = time.time(), len(done)
        with open(path, "a", encoding="utf-8") as f:
            for i in range(0, len(todo), batch):
                chunk = todo[i:i + batch]
                got = answer_batch(reader, [(it["state"], {"type": it["type"], **it["question"]}) for it in chunk])
                for it, body in zip(chunk, got):
                    rec = {"id": it["id"], "dataset": name, "type": it["type"], "expected": it["expected"], "probs": {} if isinstance(body, Exception) else probs_of(it, body)}
                    if isinstance(body, Exception):
                        rec["error"] = str(body)[:120]
                    else:
                        rec["logits"] = {k: round(v, 3) for k, v in body["logits"].items()}      # raw readout: any calibration can be redone from these
                    f.write(json.dumps(rec, ensure_ascii=False) + "\n")
                f.flush(); n += len(chunk)
                print(f"  {name} {n}/{len(items)}  {time.time() - t0:.0f}s", flush=True)
                if stop["v"]:
                    sys.exit(f"stopped at {name} {n}/{len(items)}; continue: the same command")
        print(f"== {name}: finished", flush=True)
