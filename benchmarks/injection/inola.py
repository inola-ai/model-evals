"""The detector under test through the Inola API: `POST /v1/infer`, one document per request.

    inola                       cordon-mini, the version the service serves by default
    inola:<model>[@<version>]   another model or a pinned version, e.g. inola:cordon-mini@2.2.1

Key: INOLA_API_KEY. Address: INOLA_API_URL, default https://api.inola.ai. The score is the probability of an
injection (`output.answers.injection.noul`); the service's verdict at its operating point and at each published
false-alarm point (`verdicts`) is recorded beside it. A model that is starting answers 503 with Retry-After and the
same document is asked again; 429 and 5xx likewise. A document the service declines (413 too large, 400) comes back
as `judged: false` with the reason and is never read as a clean verdict.
"""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request


class Inola:
    def __init__(self, spec: str = "inola", base_url: str | None = None, key_env: str = "INOLA_API_KEY",
                 timeout: float = 180.0, wait_s: float = 1800.0) -> None:
        kind, _, rest = spec.partition(":")
        if kind != "inola":
            raise SystemExit(f"not an Inola detector: {spec} (inola, inola:<model>[@<version>])")
        self.key = os.environ.get(key_env, "")
        if not self.key:
            raise SystemExit(f"set {key_env} to an Inola API key")
        base = base_url or os.environ.get("INOLA_API_URL") or "https://api.inola.ai"
        self.url = base.rstrip("/") + "/v1/infer"
        self.model, _, self.pinned = (rest or "cordon-mini").partition("@")
        self.timeout, self.wait_s = timeout, wait_s
        self.name = spec
        self.version = self.pinned

    def describe(self) -> dict:
        return {"api": self.url, "model": self.model, "version": self.pinned or "(service default)"}

    def _post(self, text: str) -> tuple[int, dict | str]:
        body = {"model": self.model, "input": {"state": text}}
        if self.pinned:
            body["version"] = self.pinned
        data = json.dumps(body, ensure_ascii=False).encode()
        headers = {"authorization": f"Bearer {self.key}", "content-type": "application/json",
                   "user-agent": "inola-model-evals"}
        t0, attempt = time.monotonic(), 0
        while True:
            try:
                req = urllib.request.Request(self.url, data=data, headers=headers)
                with urllib.request.urlopen(req, timeout=self.timeout) as r:
                    return 200, json.loads(r.read())
            except urllib.error.HTTPError as e:
                detail = e.read()[:300].decode("utf-8", "replace")
                if e.code in (400, 413, 422):
                    return e.code, detail
                if e.code not in (429, 500, 502, 503, 504) or time.monotonic() - t0 > self.wait_s:
                    raise RuntimeError(f"HTTP {e.code}: {detail}") from None
                retry = e.headers.get("Retry-After", "")
                delay = float(retry) if retry.replace(".", "", 1).isdigit() else 2 ** attempt * 2
            except (urllib.error.URLError, TimeoutError):
                if time.monotonic() - t0 > self.wait_s:
                    raise
                delay = 2 ** attempt * 2
            attempt += 1
            time.sleep(min(delay, 60))                       # starting, busy or a network blip: same document

    def judge(self, text: str, doc_id: str) -> dict:
        """The record written for one document."""
        code, resp = self._post(text)
        r = record(doc_id, code, resp, self.version)
        self.version = r["version"]
        return r


def record(doc_id: str, code: int, resp, version: str = "") -> dict:
    """The record of one answer of POST /v1/infer, real time or a batch line: HTTP status and the body (or the
    error text). Anything but 200 is a document not judged, with the reason."""
    if code != 200:
        return {"id": doc_id, "judged": False, "score": None, "flagged": False, "version": version,
                "reason": f"HTTP {code}: {resp}"}
    a = resp["output"]["answers"]["injection"]
    r = {"id": doc_id, "judged": True, "score": float(a["noul"]), "flagged": bool(a.get("verdict")),
         "version": resp.get("version") or version}
    if a.get("verdicts"):
        r["verdicts"] = dict(a["verdicts"])
    if a.get("threshold") is not None:
        r["threshold"] = a["threshold"]
    return r
