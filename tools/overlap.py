"""Which questions of a set share their state text with a training file (jsonl files, text anywhere in a line).

    python tools/overlap.py --sets boolq,arc --train train.jsonl val.jsonl --out results/<set>/<version>/excluded_ids.json   (one file per set: --out takes a template with {set})

Method: from the state of every question the two longest runs of plain characters (letters, digits, space, , . - ') of at least 30 characters are cut to 60 characters;
`grep -F` looks for them in the training files; a question with one hit is listed. A question without any such run cannot be checked and is counted as unchecked in the printed line.
The training data is not part of this repository: the ids alone are published, next to the numbers they are removed from."""
import argparse, json, re, subprocess, sys, tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "benchmarks"))
from decision_sets import datasets

ap = argparse.ArgumentParser(); ap.add_argument("--sets", required=True); ap.add_argument("--train", nargs="+", required=True); ap.add_argument("--out", required=True)
a = ap.parse_args()
for name in a.sets.split(","):
    keys, unchecked, n = {}, 0, 0
    for it in datasets.load(name):
        n += 1
        runs = sorted(re.findall(r"[A-Za-z0-9 ,\.\-']{30,}", it["state"]), key=len, reverse=True)[:2]
        unchecked += not runs
        for r in runs: keys[r.strip()[:60]] = it["id"]
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as f: f.write("\n".join(keys) + "\n")
    hits = subprocess.run(["grep", "-F", "-o", "-h", "-f", f.name, *a.train], capture_output=True, text=True).stdout.splitlines()
    ids = sorted({keys[h] for h in set(hits) if h in keys})
    out = Path(a.out.format(set=name)); out.parent.mkdir(parents=True, exist_ok=True); out.write_text(json.dumps(ids))
    print(f"{name}: {len(ids)} of {n} questions share text with the training files ({unchecked} could not be checked) -> {out}")
