"""<out>/*.jsonl -> summary.json and REPORT.md (+ the OpenDecisions Capability score of its own scorer)."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

from . import datasets, metrics


def _od_capability(path: Path) -> dict | None:
    spec = importlib.util.spec_from_file_location("od_score", Path(__file__).parent / "vendor" / "opendecisions_score.py")
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    tasks = {it["id"]: it["raw"] for it in datasets.load("opendecisions")}
    preds = []
    for l in open(path):
        r = json.loads(l)
        if r.get("probs"): preds.append({"id": r["id"], "probs": r["probs"]})
    try:
        return mod.score(list(tasks.values()), preds)
    except Exception as e:                                           # the vendored scorer's API is its own: a failure here must not lose the table
        return {"error": str(e)[:200]}


def build(out: Path, title: str = "") -> Path:
    summary, lines = {}, [f"# {title or out.name}", "", "| set | type | n | accuracy | NLL | ECE |", "|---|---|---|---|---|---|"]
    for p in sorted(out.glob("*.jsonl")):
        recs = [json.loads(l) for l in open(p)]
        s = metrics.summarize(recs); summary[p.stem] = s
        for g in ("all", "noul", "tfu", "choice", "score"):
            if g in s:
                x = s[g]; lines.append(f"| {p.stem} | {g} | {x['n']} | {x['acc']:.3f} ± {x['acc_se']:.3f} | {x['nll'] if x['nll'] is not None else '-'} | {x['ece'] if x['ece'] is not None else '-'} |")
        if p.stem == "opendecisions" and len(recs) == len(datasets.load("opendecisions")):          # its Capability needs every item
            cap = _od_capability(p)
            if cap: summary[p.stem]["capability"] = cap; lines += ["", f"OpenDecisions capability (its own scorer): `{json.dumps(cap)[:300]}`", ""]
    (out / "summary.json").write_text(json.dumps(summary, indent=1))
    (out / "REPORT.md").write_text("\n".join(lines) + "\n")
    return out / "REPORT.md"
