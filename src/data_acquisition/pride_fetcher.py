"""Step 1.3 — PRIDE proteomics: ATC projects (PXD030304, PXD063991). Metadata + small quantitation tables; sparsity logged."""
from __future__ import annotations

import json
from typing import Any

from src import config
from src.decisions import log_decision
from src.http_utils import download, get_json
from src.provenance import build_record, checksums_for, write_provenance

MAX_TABLE_BYTES = 200 * 1024 * 1024
TABLE_EXT = (".tsv", ".csv", ".txt", ".xlsx", ".txt.gz", ".tsv.gz", ".csv.gz")


def list_files(accession: str) -> list[dict[str, Any]]:
    out, page = [], 0
    while True:
        batch = get_json(f"{config.PRIDE_API}/projects/{accession}/files",
                         params={"pageSize": 100, "page": page})
        if not batch:
            return out
        out.extend(batch)
        page += 1


def ftp_url(f: dict[str, Any]) -> str | None:
    for loc in f.get("publicFileLocations", []):
        if loc.get("name") == "FTP Protocol":
            return loc["value"].replace("ftp://", "https://", 1)
    return None


def fetch_project(accession: str, force: bool = False) -> str:
    out_dir = config.DATA_RAW / "PRIDE" / accession
    out_dir.mkdir(parents=True, exist_ok=True)
    try:
        meta = get_json(f"{config.PRIDE_API}/projects/{accession}")
        files = list_files(accession)
    except Exception as exc:
        log_decision("data gap", f"PRIDE {accession} unavailable", str(exc))
        write_provenance(f"PRIDE_{accession}", build_record(
            source="PRIDE", accession=accession, url=f"https://www.ebi.ac.uk/pride/archive/projects/{accession}",
            modality="proteomics", platform="n/a", license="CC0", status="not_available",
            notes=f"PRIDE project metadata not retrievable: {exc}"))
        return f"PRIDE_{accession}"

    (out_dir / "project_metadata.json").write_text(json.dumps(meta, indent=1), encoding="utf-8")
    (out_dir / "file_listing.json").write_text(json.dumps(files, indent=1), encoding="utf-8")
    fetched = [out_dir / "project_metadata.json", out_dir / "file_listing.json"]
    for f in files:
        name = f.get("fileName", "")
        if f.get("fileCategory", {}).get("value") in ("RESULT", "OTHER") and name.lower().endswith(TABLE_EXT) \
                and f.get("fileSizeBytes", 0) <= MAX_TABLE_BYTES and (url := ftp_url(f)):
            try:
                fetched.append(download(url, out_dir / name, force=force)["path"])
            except Exception as exc:
                log_decision("data gap", f"PRIDE {accession}: {name} download failed", str(exc))
    quant = len(fetched) - 2
    log_decision("data finding", f"PRIDE {accession} proteomics sparsity",
                 f"{len(files)} files listed; {quant} quantitation-style tables downloaded (sparse ATC proteomics expected).")
    write_provenance(f"PRIDE_{accession}", build_record(
        source="PRIDE Archive", accession=accession, url=f"https://www.ebi.ac.uk/pride/archive/projects/{accession}",
        sample_count=len(meta.get("sampleProcessingProtocol", "")) and "see metadata" or "n/a",
        modality="proteomics", platform=", ".join(i.get("name", "") for i in meta.get("instruments", [])) or "n/a",
        license="CC0 (PRIDE public data)",
        raw_files=[p.name for p in fetched], checksums=checksums_for(fetched, out_dir),
        notes=f"{meta.get('title', '')}. {len(files)} files in project; {quant} quantitation tables retrieved. Sparse ATC coverage.",
        n_project_files=len(files), n_quant_tables=quant, title=meta.get("title"),
    ))
    return f"PRIDE_{accession}"


def run(force: bool = False, **_: Any) -> list[str]:
    return [fetch_project(a, force) for a in config.PRIDE_ACCESSIONS]
