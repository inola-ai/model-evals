"""Rebuilds the results table of models/<model>/README.md between the markers <!-- results --> and <!-- /results --> from every results/<set>/<version>/metrics.json.

    python tools/build_page.py models/decider"""
import json, sys
from pathlib import Path
d = Path(sys.argv[1]); rows = []
LABEL = {"jevbench": "JevBench public items", "boolq": "BoolQ (validation)", "arc": "ARC-Challenge (test)", "helpsteer": "HelpSteer (validation, helpfulness 0-4)", "decision-questions": "decision-questions"}
for m in sorted(d.glob("results/*/*/metrics.json")):
    s, v = m.parent.parent.name, m.parent.name
    for kind, x in json.loads(m.read_text()).items():
        rows.append(f"| {v} | {LABEL.get(s, s)} | `{kind}` | {x['questions']} | {x['accuracy']:.3f} ± {x['accuracy_se']:.3f} | {x['nll']:.3f} | {x['left_out']} |")
table = "| version | set | kind | questions | accuracy | NLL | left out |\n|---|---|---|---|---|---|---|\n" + "\n".join(rows)
p = d / "README.md"; t = p.read_text(); a, b = t.index("<!-- results -->") + len("<!-- results -->"), t.index("<!-- /results -->")
p.write_text(t[:a] + "\n\n" + table + "\n\n" + t[b:]); print(f"{len(rows)} rows -> {p}")
