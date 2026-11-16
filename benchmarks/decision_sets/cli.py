"""inola-bench: run a decision model over the public sets and write the report.

    inola-bench list
    inola-bench run --model inola-ai/decider-open --out results/open [--sets all] [--limit 200] 
    inola-bench report results/open
"""
from __future__ import annotations

import argparse
from pathlib import Path

from . import datasets, report, runner


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(prog="inola-bench")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list")
    r = sub.add_parser("run"); r.add_argument("--model", required=True, help="a model directory or a Hub id (a typecastlm-format checkpoint: prompt.json with the calibration temperatures beside the weights)")
    r.add_argument("--out", required=True); r.add_argument("--sets", default="all"); r.add_argument("--limit", type=int, default=0)
    r.add_argument("--prompt", default="", help="a prompt.json to use instead of the one beside the weights"); r.add_argument("--device", default=None); r.add_argument("--batch", type=int, default=64)
    p = sub.add_parser("report"); p.add_argument("out")
    a = ap.parse_args(argv)
    if a.cmd == "list":
        for k, v in datasets.DATASETS.items():
            print(f"{k:22s} {v['repo']:40s} {v['note']}")
        return
    if a.cmd == "run":
        from typecastlm.server import Reader
        names = list(datasets.LOADERS) if a.sets == "all" else a.sets.split(",")
        rd = Reader(a.model, device=a.device or "auto", prompt=a.prompt or None)
        print(f"model {a.model}: {rd.describe()}", flush=True)
        out = Path(a.out); runner.run(rd, names, out, a.limit, a.batch)
        print(f"report: {report.build(out, a.model)}")
        return
    print(f"report: {report.build(Path(a.out))}")


if __name__ == "__main__":
    main()
