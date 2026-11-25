"""The model under test: the Inola API, `POST /v1/infer` (inola.py beside these packages).

    inola                       cordon-mini, the version the service serves by default
    inola:<model>[@<version>]   another model or a pinned version, e.g. inola:cordon-mini@2.2.1
"""
from __future__ import annotations

from inola import Inola


def make(spec: str, base_url: str | None = None) -> Inola:
    return Inola(spec, base_url=base_url)
