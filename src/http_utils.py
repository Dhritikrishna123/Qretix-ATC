"""HTTP helpers: retrying session, resumable downloads with checksums, NCBI rate limiting."""
from __future__ import annotations

import hashlib
import threading
import time
from pathlib import Path
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from src import config

_session: requests.Session | None = None
_ncbi_lock = threading.Lock()
_ncbi_last = 0.0


def get_session() -> requests.Session:
    global _session
    if _session is None:
        s = requests.Session()
        retry = Retry(
            total=5,
            backoff_factor=1.5,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=None,
        )
        s.mount("https://", HTTPAdapter(max_retries=retry))
        s.mount("http://", HTTPAdapter(max_retries=retry))
        s.headers["User-Agent"] = config.USER_AGENT
        _session = s
    return _session


def request(method: str, url: str, *, timeout: int = 120, **kw: Any) -> requests.Response:
    resp = get_session().request(method, url, timeout=timeout, **kw)
    resp.raise_for_status()
    return resp


def get_json(url: str, **kw: Any) -> Any:
    return request("GET", url, **kw).json()


def sha256_file(path: Path, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(chunk), b""):
            h.update(block)
    return h.hexdigest()


def download(url: str, dest: Path, *, force: bool = False, **kw: Any) -> dict[str, Any]:
    """Stream ``url`` to ``dest`` (atomic via .part with HTTP Range resume). Skips if present unless ``force``.

    Returns ``{"path", "size", "sha256"}``.
    """
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size > 0 and not force:
        return {"path": dest, "size": dest.stat().st_size, "sha256": sha256_file(dest)}
    part = dest.with_suffix(dest.suffix + ".part")
    headers = dict(kw.pop("headers", {}))
    existing = part.stat().st_size if part.exists() and not force else 0
    if existing > 0:
        headers["Range"] = f"bytes={existing}-"
    
    with get_session().request("GET", url, stream=True, timeout=300, headers=headers, **kw) as r:
        if r.status_code == 206:
            # Resuming
            mode = "ab"
        elif r.status_code == 200:
            mode = "wb"
        else:
            r.raise_for_status()
            mode = "wb"
        with open(part, mode) as fh:
            for block in r.iter_content(chunk_size=1 << 20):
                if block:
                    fh.write(block)
    part.replace(dest)
    return {"path": dest, "size": dest.stat().st_size, "sha256": sha256_file(dest)}


def ncbi_get(endpoint: str, params: dict[str, Any], *, as_json: bool = False) -> requests.Response | Any:
    """Rate-limited call to NCBI E-utilities (``endpoint`` e.g. ``esearch.fcgi``)."""
    global _ncbi_last
    params = dict(params)
    params.setdefault("tool", "qretix-atc")
    params.setdefault("email", config.NCBI_EMAIL)
    if config.NCBI_API_KEY:
        params["api_key"] = config.NCBI_API_KEY
    with _ncbi_lock:
        wait = config.NCBI_MIN_INTERVAL - (time.monotonic() - _ncbi_last)
        if wait > 0:
            time.sleep(wait)
        _ncbi_last = time.monotonic()
    # POST handles long query strings (e.g. big ID lists / WebEnv).
    resp = request("POST", f"{config.NCBI_EUTILS}/{endpoint}", data=params)
    return resp.json() if as_json else resp
