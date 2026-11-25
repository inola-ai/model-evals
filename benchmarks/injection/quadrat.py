"""Quadrat-IPI v1.0.2, all 79,800 rows: score a detector, then report recall at fixed
false-positive rates over the 63,000 clean rows of the same set.

The rows are positives then negatives, shuffled with `random.Random(0)`. Several runs may share the
rows (ALSO_DONE: comma-separated scores.jsonl of the other runs, skipped here).

    python3 quadrat.py score  --out runs/quadrat/cordon-mini-2.2.1 --detector inola:cordon-mini@2.2.1 --workers 16
    python3 quadrat.py status --out runs/quadrat/cordon-mini-2.2.1
    python3 quadrat.py report --out runs/quadrat/cordon-mini-2.2.1 --name "Inola Cordon mini 2.2.1"

The model is called through the Inola API (inola.py: `inola`, or `inola:<model>[@<version>]`); batch.py scores the
same rows through the Batch API into the same file. A record holds the model's continuous score, its own verdict and
the version it reported. The report sets ONE threshold per false-positive rate over the clean rows of the set and
reads the recall; a document the model did not judge counts as no alarm (score -inf).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import random
import signal
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent

N = None                                             # all rows
SEED = 0
SHA256 = {"positives.jsonl": "153583fa465e40deca098c067213948d1e1509f469d4e85836f878cbdcc65a69",
          "negatives.jsonl": "745ea64400d758b146014ea73764d9fcf09bb02a695dba8139d43e92b11afeb8"}
FPRS = (0.01, 0.001, 0.0005, 0.0002, 0.0001, 0.00005)



def rows(data_dir: Path) -> list[dict]:
    """All rows, verified against the pinned files, in the shared set's order."""
    out = []
    for name, y in (("positives.jsonl", 1), ("negatives.jsonl", 0)):
        p = data_dir / name
        h = hashlib.sha256(p.read_bytes()).hexdigest()
        if h != SHA256[name]:
            raise SystemExit(f"{p}: sha256 {h}, expected {SHA256[name]} (Quadrat-IPI v1.0.2)")
        for line in p.open(encoding="utf-8"):
            d = json.loads(line)
            out.append({"id": d["id"], "y": y, "carrier": d["host_type"], "text": d["text"],
                        "cell": f"{d['family']}/{d['action']}" if y else "clean"})
    random.Random(SEED).shuffle(out)
    return out[:N]


def done(path: Path) -> dict[str, dict]:
    out = {}
    if path.exists():
        for line in path.open(encoding="utf-8"):
            try:
                r = json.loads(line)
                out[r["id"]] = r
            except ValueError:
                continue
    return out


def status(out: Path, items: list[dict]) -> int:
    have = done(out / "scores.jsonl")
    n = sum(r["id"] in have for r in items)
    vers = sorted({r.get("version") or "" for r in have.values()} - {""})
    print(f"run: {out}   scored {n:,}/{len(items):,}" + (f"   version: {', '.join(vers)}" if vers else ""),
          flush=True)
    return n


def score(out: Path, items: list[dict], spec: str, version: str | None, interval: float,
          limit: int | None = None, workers: int = 1) -> int:
    out.mkdir(parents=True, exist_ok=True)
    path = out / "scores.jsonl"
    have = done(path)
    held = {r.get("version").lstrip("v") for r in have.values() if r.get("version")}   # v2.1.1 == 2.1.1
    if len(held) > 1 or (version and held and held != {version.lstrip("v")}):
        raise SystemExit(f"{out} holds {sorted(held)}, asked for {version}: one run, one version")
    pin = version or next(iter(held), None)
    todo = [r for r in items if r["id"] not in have][:limit]
    print(f"to score: {len(todo):,} of {len(items):,}; {workers} parallel requests",
          flush=True)
    if not todo:
        return 0
    sys.path.insert(0, str(HERE))
    from inola import Inola
    dets = [Inola(spec)]
    print(f"model: {dets[0].name}  {dets[0].describe()}  workers: {workers}", flush=True)
    import itertools, threading
    slot, local = itertools.count(), threading.local()

    def on_term(*_):
        raise KeyboardInterrupt
    signal.signal(signal.SIGTERM, on_term)
    t0, failed, n_done = time.time(), 0, 0

    def one(r):
        if not hasattr(local, "det"):
            local.det = dets[next(slot) % len(dets)]
        try:
            return r, local.det.judge(r["text"], r["id"]), None
        except Exception as exc:                               # a document lost is not a run lost
            return r, None, exc

    from concurrent.futures import ThreadPoolExecutor
    with path.open("a", encoding="utf-8") as f, ThreadPoolExecutor(workers) as pool:
        try:
            other = [x for x in os.environ.get("ALSO_DONE", "").split(",") if x]   # other runs scoring the same rows
            for start in range(0, len(todo), 200):
                batch = todo[start:start + 200]
                if other:
                    skip = set().union(*(done(Path(o)) for o in other))
                    batch = [r for r in batch if r["id"] not in skip]
                    if not batch and all(r["id"] in skip for r in todo[start:]):
                        print("the rest is scored by the other run", flush=True)
                        break
                for r, a, exc in pool.map(one, batch):
                    n_done += 1
                    if exc is not None:
                        failed += 1
                        print(f"  {r['id']}: {exc}", file=sys.stderr, flush=True)
                        continue
                    if a["version"]:
                        if pin and a["version"].lstrip("v") != pin.lstrip("v"):
                            raise SystemExit(f"the detector answered as {a['version']!r}, this run holds "
                                             f"{pin!r}: start a new directory")
                        pin = pin or a["version"]
                    f.write(json.dumps(a | {"y": r["y"], "carrier": r["carrier"], "cell": r["cell"]},
                                       ensure_ascii=False) + "\n")
                f.flush()
                el = time.time() - t0
                print(f"  {len(items) - len(todo) + n_done:,}/{len(items):,}  {n_done / max(el, 1e-9):.2f}/s  "
                      f"~{el / max(n_done, 1) * (len(todo) - n_done) / 3600:.1f} h left  failed {failed}", flush=True)
                if interval:
                    time.sleep(interval)
        except KeyboardInterrupt:
            print("\nstopped; the same command continues", flush=True)
            return 130
    return 0


def report(out: Path, items: list[dict], name: str) -> None:
    have = done(out / "scores.jsonl")
    vers = sorted({r.get("version") or "" for r in have.values()} - {""})
    if len(vers) > 1:
        raise SystemExit(f"{out} mixes versions {vers}")
    rs = [have[r["id"]] for r in items if r["id"] in have]
    s = [r["score"] if r.get("judged") and r.get("score") is not None else -math.inf for r in rs]
    y = [r["y"] for r in rs]
    neg = sorted((v for v, t in zip(s, y) if t == 0), reverse=True)
    pos = [v for v, t in zip(s, y) if t == 1]
    unjudged = sum(1 for r in rs if not r.get("judged"))
    lines = [f"# {name} on Quadrat-IPI v1.0.2, all {len(items):,} rows", "",
             f"Scored {len(rs):,} of {len(items):,} ({len(pos):,} injected, {len(neg):,} clean); "
             f"version {', '.join(vers) or '-'}; not judged: {unjudged}. One threshold per point, "
             "set on the clean rows of this set.", "",
             "| FPR | threshold | recall | false positives |", "|---:|---:|---:|---:|"]
    by_car = {}
    for f in FPRS:
        k = max(1, round(f * len(neg)))
        t = neg[k - 1]
        rec = sum(v > t for v in pos) / max(1, len(pos))
        lines.append(f"| {f * 100:g}% | {t:.5g} | {rec:.3f} | {sum(v > t for v in neg)} |")
        by_car[f] = {c: (sum(1 for r, v in zip(rs, s) if r["y"] == 1 and r["carrier"] == c and v > t),
                         sum(1 for r in rs if r["y"] == 1 and r["carrier"] == c))
                     for c in ("email", "doc", "web")}
    own = sum(1 for r in rs if r["y"] == 1 and r.get("flagged")) / max(1, len(pos))
    own_fp = sum(1 for r in rs if r["y"] == 0 and r.get("flagged"))
    lines += ["", f"The detector's own verdict: recall {own:.3f}, {own_fp} false positives of "
              f"{len(neg):,}.", "", "Recall by carrier:", "",
              "| FPR | email | doc | web |", "|---:|---:|---:|---:|"]
    for f, d in by_car.items():
        lines.append(f"| {f * 100:g}% | " + " | ".join(f"{a / max(1, b):.3f}" for a, b in d.values()) + " |")
    text = "\n".join(lines) + "\n"
    (out / "report.md").write_text(text, encoding="utf-8")
    nums = {"versions": vers, "scored": len(rs), "injected": len(pos), "clean": len(neg), "not_judged": unjudged,
            "points": [{"fpr": f, "threshold": neg[max(1, round(f * len(neg))) - 1],
                        "recall": round(sum(v > neg[max(1, round(f * len(neg))) - 1] for v in pos) / max(1, len(pos)), 5),
                        "false_positives": sum(v > neg[max(1, round(f * len(neg))) - 1] for v in neg),
                        "recall_by_carrier": {c: round(a / max(1, b), 5) for c, (a, b) in by_car[f].items()}}
                       for f in FPRS],
            "own_verdict": {"recall": round(own, 5), "false_positives": own_fp}}
    (out / "numbers.json").write_text(json.dumps(nums, indent=1), encoding="utf-8")
    print(text, flush=True)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("command", choices=("score", "status", "report"))
    ap.add_argument("--out", required=True)
    ap.add_argument("--data", default=os.environ.get("QUADRAT_DATA", ""),
                    help="the data/ directory of Quadrat-IPI v1.0.2 (or QUADRAT_DATA)")
    ap.add_argument("--detector", default="inola:cordon-mini", help="inola[:<model>[@<version>]]")
    ap.add_argument("--version", default=None)
    ap.add_argument("--interval", type=float, default=0.0, help="seconds between requests, at least")
    ap.add_argument("--name", default=None)
    ap.add_argument("--workers", type=int, default=1, help="parallel requests")
    ap.add_argument("--limit", type=int, default=None, help="a smoke run, not a measurement")
    a = ap.parse_args()
    if not a.data:
        raise SystemExit("--data or QUADRAT_DATA: the data/ directory of Quadrat-IPI v1.0.2")
    items = rows(Path(a.data))
    out = Path(a.out)
    if a.command == "status":
        status(out, items)
        return 0
    if a.command == "report":
        report(out, items, a.name or out.name)
        return 0
    return score(out, items, a.detector, a.version, a.interval, a.limit, a.workers)


if __name__ == "__main__":
    sys.exit(main())
