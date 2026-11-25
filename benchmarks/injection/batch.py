"""Score an injection benchmark of this directory through the Inola Batch API instead of one request per document.

    python3 batch.py llmail    --out runs/llmail/<run>    --spec inola:cordon-mini@2.2.1
    python3 batch.py quadrat   --out runs/quadrat/<run>   --spec inola:cordon-mini@2.2.1   (QUADRAT_DATA or --data)
    python3 batch.py notinject --out runs/notinject/<run> --spec inola:cordon-mini@2.2.1
    python3 batch.py quadrat   --out runs/quadrat/<run>   --spec ... --online   real time from the end of the list,
                                                                              beside a running batch
    ... --status                    what is on disk and which batches are open; asks nothing

The documents not yet in `<out>/scores.jsonl` are written as `POST /v1/infer` lines (custom_id = document id), in
files of at most --lines lines and 200 MB, uploaded (`POST /v1/files`) and run as batches (`POST /v1/batches`), one
at a time. Each answer becomes the same record as in real time (`inola.record`) and is appended to `scores.jsonl`;
the benchmark's own `report` reads it as before. Open batches are kept in `<out>/batches.json`: a stopped run picks
them up again instead of submitting the documents twice. A line the service refuses (too long, invalid) is a
document not judged, with the reason. Key: INOLA_API_KEY; address: INOLA_API_URL (default https://api.inola.ai).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))                 # inola.py, quadrat.py and the benchmark packages
FINAL = {"completed", "failed", "cancelled", "expired"}
MAX_BYTES = 200 * 2**20


def documents(bench: str, data: str | None) -> tuple[list[tuple[str, str]], dict, object]:
    """[(id, text)], {id: extra fields of the record}, record function of the benchmark."""
    if bench == "llmail":
        from llmail_eval import data as d
        from inola import record
        return [(e.id, e.text) for e in d.emails(Path(data or HERE / "data/llmail"))], {}, record
    if bench == "notinject":
        from notinject_eval import data as d
        from inola import record
        return [(p.id, p.text) for p in d.prompts(Path(data or HERE / "data/notinject"))], {}, record
    if bench == "quadrat":
        import quadrat as q
        from inola import record
        rows = q.rows(Path(data or os.environ.get("QUADRAT_DATA", "")))
        extra = {r["id"]: {"y": r["y"], "carrier": r["carrier"], "cell": r["cell"]} for r in rows}
        return [(r["id"], r["text"]) for r in rows], extra, record
    raise SystemExit(f"unknown benchmark {bench}: llmail, notinject, quadrat")


class Api:
    def __init__(self) -> None:
        self.key = os.environ.get("INOLA_API_KEY", "")
        if not self.key:
            raise SystemExit("set INOLA_API_KEY to an Inola API key")
        self.base = (os.environ.get("INOLA_API_URL") or "https://api.inola.ai").rstrip("/")

    def call(self, method: str, path: str, body: bytes | None = None, ctype: str | None = None,
             raw: bool = False):
        for attempt in range(8):
            req = urllib.request.Request(self.base + path, data=body, method=method,
                                         headers={"authorization": f"Bearer {self.key}", "user-agent": "inola-model-evals",
                                                  **({"content-type": ctype} if ctype else {})})
            try:
                with urllib.request.urlopen(req, timeout=600) as r:
                    data = r.read()
                    return data if raw else json.loads(data)
            except urllib.error.HTTPError as e:
                detail = e.read()[:500].decode("utf-8", "replace")
                if e.code in (500, 502, 503, 504, 507) and attempt < 7:
                    ra = e.headers.get("Retry-After", "")
                    time.sleep(min(float(ra) if ra.replace(".", "", 1).isdigit() else 2 ** attempt * 5, 120))
                    continue
                raise SystemExit(f"{method} {path}: HTTP {e.code}: {detail}") from None
            except (urllib.error.URLError, TimeoutError) as e:
                if attempt < 7:
                    time.sleep(2 ** attempt * 5)
                    continue
                raise SystemExit(f"{method} {path}: {e}") from None

    def upload(self, name: str, content: bytes) -> str:
        b = uuid.uuid4().hex
        body = (f"--{b}\r\nContent-Disposition: form-data; name=\"purpose\"\r\n\r\nbatch\r\n"
                f"--{b}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"{name}\"\r\n"
                f"Content-Type: application/jsonl\r\n\r\n").encode() + content + f"\r\n--{b}--\r\n".encode()
        return self.call("POST", "/v1/files", body, f"multipart/form-data; boundary={b}")["id"]


def load_done(path: Path) -> set[str]:
    out = set()
    if path.exists():
        for line in path.open(encoding="utf-8"):
            try:
                out.add(json.loads(line)["id"])
            except ValueError:
                continue
    return out


def chunks(todo, model, version, max_lines, max_chars):
    """Batch files: at most max_lines lines, 200 MB, and max_chars characters of documents (the plan caps the
    characters of unfinished batch work: 200 M on Pro)."""
    lines, size, chars = [], 0, 0
    for doc_id, text in todo:
        body = {"model": model, "input": {"state": text}}
        if version:
            body["version"] = version
        ln = (json.dumps({"custom_id": doc_id, "url": "/v1/infer", "body": body}, ensure_ascii=False) + "\n").encode()
        if lines and (len(lines) >= max_lines or size + len(ln) > MAX_BYTES or chars + len(text) > max_chars):
            yield lines
            lines, size, chars = [], 0, 0
        lines.append(ln)
        size += len(ln)
        chars += len(text)
    if lines:
        yield lines


def collect(api: Api, b: dict, out: Path, extra: dict, record, version: str) -> int:
    """Append the answers of a finished batch that are not on disk yet. Returns how many were written."""
    have, n = load_done(out / "scores.jsonl"), 0
    with (out / "scores.jsonl").open("a", encoding="utf-8") as fh:
        for key in ("output_file_id", "error_file_id"):
            if not b.get(key):
                continue
            for raw in api.call("GET", f"/v1/files/{b[key]}/content", raw=True).decode("utf-8").splitlines():
                if not raw.strip():
                    continue
                line = json.loads(raw)
                cid = line.get("custom_id")
                if not cid or cid in have:
                    continue
                resp = line.get("response") or {}
                if line.get("error") is None and resp.get("status_code") == 200:
                    r = record(cid, 200, resp["body"], version)
                else:
                    err = line.get("error") or resp.get("body") or resp
                    r = record(cid, resp.get("status_code") or 0, json.dumps(err, ensure_ascii=False)[:300], version)
                fh.write(json.dumps(r | extra.get(cid, {}), ensure_ascii=False) + "\n")
                have.add(cid)
                n += 1
    return n


def online(bench: str, docs, extra, spec: str, out: Path, workers: int, limit: int | None) -> int:
    """Real time beside a running batch: the documents not on disk, from the END of the list (a batch takes them from
    the start), one POST /v1/infer each, appended to the same scores.jsonl."""
    import threading
    from concurrent.futures import ThreadPoolExecutor
    from inola import Inola
    det = Inola(spec)
    done = load_done(out / "scores.jsonl")
    todo = [(i, t) for i, t in reversed(docs) if i not in done][:limit]
    print(f"online: {len(todo):,} documents from the end of the list, {workers} at a time", flush=True)
    lock, stop, n, t0 = threading.Lock(), threading.Event(), [0, 0], time.time()

    def one(item):
        doc_id, text = item
        if stop.is_set():
            return
        if doc_id in load_done_cache:                       # answered by a batch meanwhile
            return
        try:
            r = det.judge(text, doc_id)
        except Exception as exc:                            # noqa: BLE001 - asked again next run
            with lock:
                n[1] += 1
                print(f"  {doc_id}: {exc}", flush=True)
            return
        with lock:
            fh.write(json.dumps(r | extra.get(doc_id, {}), ensure_ascii=False) + "\n")
            fh.flush()
            n[0] += 1
            if n[0] % 500 == 0:
                print(f"  online {n[0]:,}/{len(todo):,}  {n[0] / (time.time() - t0):.1f}/s  failed {n[1]}", flush=True)

    load_done_cache = set()
    with (out / "scores.jsonl").open("a", encoding="utf-8") as fh, ThreadPoolExecutor(workers) as pool:
        try:
            for start in range(0, len(todo), 2000):
                load_done_cache = load_done(out / "scores.jsonl")
                list(pool.map(one, todo[start:start + 2000]))
        except KeyboardInterrupt:
            stop.set()
            print("\nstopping after the requests in flight...", flush=True)
            return 130
    print(f"online: written {n[0]:,}, failed {n[1]}", flush=True)
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("bench", choices=("llmail", "notinject", "quadrat"))
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--spec", default="inola:cordon-mini")
    ap.add_argument("--data", default=None)
    ap.add_argument("--lines", type=int, default=25000, help="lines per batch file (the service takes up to 50,000)")
    ap.add_argument("--max-chars", type=int, default=150_000_000,
                    help="characters of documents per batch (below the plan's cap on unfinished batch work)")
    ap.add_argument("--limit", type=int, default=None, help="only the first N documents (a smoke run)")
    ap.add_argument("--online", action="store_true", help="real time from the end of the list, beside a batch")
    ap.add_argument("--workers", type=int, default=16, help="--online: requests in flight")
    ap.add_argument("--status", action="store_true")
    a = ap.parse_args()
    docs, extra, record = documents(a.bench, a.data)
    docs = docs[:a.limit] if a.limit else docs
    model, _, version = (a.spec.partition(":")[2] or "cordon-mini").partition("@")
    a.out.mkdir(parents=True, exist_ok=True)
    state_p = a.out / "batches.json"
    state = json.loads(state_p.read_text()) if state_p.exists() else []
    save = lambda: state_p.write_text(json.dumps(state, indent=1))
    done = load_done(a.out / "scores.jsonl")
    print(f"{a.bench}: {len(done & {d for d, _ in docs}):,}/{len(docs):,} on disk; "
          f"open batches: {[s['id'] for s in state if not s.get('collected')]}", flush=True)
    if a.status:
        return 0
    if a.online:
        return online(a.bench, docs, extra, a.spec, a.out, a.workers, a.limit)
    api = Api()
    try:
        while True:
            open_b = [s for s in state if not s.get("collected")]
            if not open_b:
                done = load_done(a.out / "scores.jsonl")
                todo = [(i, t) for i, t in docs if i not in done]
                if not todo:
                    break
                lines = next(chunks(todo, model, version, a.lines, a.max_chars))
                fid = api.upload(f"{a.bench}-{len(state)}.jsonl", b"".join(lines))
                b = api.call("POST", "/v1/batches", json.dumps({"input_file_id": fid, "completion_window": "24h",
                             "metadata": {"source": f"model-evals {a.bench}"}}).encode(), "application/json")
                state.append({"id": b["id"], "lines": len(lines), "created": time.strftime("%F %T")})
                save()
                print(f"submitted {b['id']}: {len(lines):,} documents ({len(todo):,} left before it)", flush=True)
                continue
            s = open_b[0]
            b = api.call("GET", f"/v1/batches/{s['id']}")
            c = b.get("request_counts") or {}
            eta = b.get("estimated_completion_at")
            print(f"  {time.strftime('%T')}  {s['id']}  {b['status']}  {c.get('completed', 0):,}+{c.get('failed', 0):,}"
                  f"/{c.get('total', s['lines']):,}" + (f"  eta {time.strftime('%T', time.localtime(eta))}" if eta else ""),
                  flush=True)
            if b["status"] in FINAL:
                n = collect(api, b, a.out, extra, record, version)
                s.update(collected=True, status=b["status"], written=n, usage=b.get("usage"))
                save()
                print(f"  {s['id']} {b['status']}: {n:,} answers written", flush=True)
                if b["status"] != "completed" and n == 0:
                    raise SystemExit(f"batch {s['id']} ended {b['status']} with no answers: {json.dumps(b)[:500]}")
                continue
            time.sleep(min(max((eta or 0) - time.time(), 30), 120))
    except KeyboardInterrupt:
        print(f"\nstopped; open batches stay in {state_p} and are picked up by the same command", flush=True)
        return 130
    done = load_done(a.out / "scores.jsonl")
    print(f"{a.bench}: {len(done & {d for d, _ in docs}):,}/{len(docs):,} on disk; done", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
