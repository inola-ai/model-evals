"""metrics.json of a run: per set and kind accuracy with its binomial standard error, NLL of the right answer, ECE of the confidence in the most probable answer (10 equal-width bins), questions counted and questions left out.

    python tools/build_metrics.py <answers.jsonl> [--excluded excluded_ids.json] --out metrics.json

Questions of kind `tfu` (a third answer, "unknown") are not scored. Excluded ids (state text shared with the training data, see tools/overlap.py) are left out of every number."""
import argparse, json, math
from pathlib import Path

ap = argparse.ArgumentParser(); ap.add_argument("answers"); ap.add_argument("--excluded", default=""); ap.add_argument("--out", required=True); a = ap.parse_args()
ex = set(json.loads(Path(a.excluded).read_text())) if a.excluded else set()
rows = [json.loads(l) for l in open(a.answers) if l.strip()]
out = {}
for kind in sorted({r["type"] for r in rows} - {"tfu"}):
    rs = [r for r in rows if r["type"] == kind]; keep = [r for r in rs if r["id"] not in ex]
    hit = [1.0 if r["probs"] and max(r["probs"], key=r["probs"].get) == r["expected"] else 0.0 for r in keep]          # an item that could not be asked is wrong
    nll = [-math.log(max(r["probs"].get(r["expected"], 0.0), 1e-6)) for r in keep if r["probs"]]
    n = len(keep); m = sum(hit) / n
    bins = {}
    for r, h in zip(keep, hit):
        if r["probs"]:
            c = max(r["probs"].values()); b = bins.setdefault(min(int(c * 10), 9), [0, 0.0, 0.0]); b[0] += 1; b[1] += c; b[2] += h
    answered = sum(b[0] for b in bins.values()); ece = sum(abs(b[1] - b[2]) for b in bins.values()) / answered
    out[kind] = {"questions": n, "left_out": len(rs) - n, "accuracy": round(m, 4), "accuracy_se": round(math.sqrt(m * (1 - m) / n), 4), "nll": round(sum(nll) / len(nll), 4), "ece": round(ece, 4)}
Path(a.out).write_text(json.dumps(out, indent=1)); print(json.dumps(out))
