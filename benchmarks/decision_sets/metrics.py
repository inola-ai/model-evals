"""One scoring for every set: per set and question type, accuracy (the most probable key is the right one; a row that could not be asked is wrong),
mean NLL of the right key (probability floored at 1e-6, rows that were answered), top-probability ECE (10 bins) and, for tfu, the unsure rate."""
from __future__ import annotations

import math
from collections import defaultdict


def row_facts(rec: dict) -> dict:
    p = rec.get("probs") or {}
    if not p or rec["expected"] not in p:
        return {"valid": False, "hit": 0.0}
    top = max(sorted(p), key=lambda k: p[k])
    return {"valid": True, "hit": float(top == rec["expected"]), "nll": -math.log(max(p[rec["expected"]], 1e-6)), "conf": p[top], "unsure": float(top == "unknown")}


def ece(pairs: list[tuple[float, float]], bins: int = 10) -> float | None:
    if not pairs:
        return None
    acc = defaultdict(lambda: [0, 0.0, 0.0])
    for c, y in pairs:
        b = acc[min(int(c * bins), bins - 1)]
        b[0] += 1; b[1] += c; b[2] += y
    return sum(n / len(pairs) * abs(o / n - f / n) for n, f, o in acc.values())


def summarize(recs: list[dict]) -> dict:
    """{"all": {...}, "noul": {...}, ...}: n, answered, acc, acc_se (binomial), nll, ece, unsure_rate (tfu)"""
    groups = defaultdict(list)
    for r in recs:
        groups["all"].append(r); groups[r["type"]].append(r)
    out = {}
    for g, rs in groups.items():
        f = [row_facts(r) for r in rs]
        ok = [x for x in f if x["valid"]]
        n = len(rs); acc = sum(x["hit"] for x in f) / n
        out[g] = {"n": n, "answered": len(ok), "acc": round(acc, 4), "acc_se": round(math.sqrt(acc * (1 - acc) / n), 4),
                  "nll": round(sum(x["nll"] for x in ok) / len(ok), 4) if ok else None,
                  "ece": round(ece([(x["conf"], x["hit"]) for x in ok]) or 0.0, 4) if ok else None}
        if g == "tfu" and ok:
            out[g]["unsure_rate"] = round(sum(x["unsure"] for x in ok) / len(ok), 4)
    return out
