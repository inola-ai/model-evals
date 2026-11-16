"""<out>/*.jsonl -> summary.json and REPORT.md."""
from __future__ import annotations

import json
from pathlib import Path

from . import datasets, metrics


def build(out: Path, title: str = "") -> Path:
    summary, lines = {}, [f"# {title or out.name}", "", "| set | type | n | accuracy | NLL | ECE |", "|---|---|---|---|---|---|"]
    for p in sorted(out.glob("*.jsonl")):
        recs = [json.loads(l) for l in open(p)]
        s = metrics.summarize(recs); summary[p.stem] = s
        for g in ("all", "noul", "tfu", "choice", "score"):
            if g in s:
                x = s[g]; lines.append(f"| {p.stem} | {g} | {x['n']} | {x['acc']:.3f} ± {x['acc_se']:.3f} | {x['nll'] if x['nll'] is not None else '-'} | {x['ece'] if x['ece'] is not None else '-'} |")
    (out / "summary.json").write_text(json.dumps(summary, indent=1))
    (out / "REPORT.md").write_text("\n".join(lines) + "\n")
    return out / "REPORT.md"
