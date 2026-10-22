"""Step 1.1 — Transcriptomics (NCBI GEO).

* GSE193581 (scRNA-seq) and GSE76039 (bulk microarray + mutation): series matrix,
  SOFT family file, supplementary files, per-sample metadata table.
* GSM7030310: verify whether it is standalone or part of GSE193581.
* GEO DataSets (GDS) search for anaplastic thyroid cancer.
"""
from __future__ import annotations

import gzip
import re
from pathlib import Path
from typing import Any

import pandas as pd

from src import config
from src.decisions import log_decision
from src.http_utils import download, get_json, ncbi_get, request
from src.provenance import build_record, checksums_for, write_provenance

LICENSE = "Public domain (GEO submission agreement)"


def series_dir_url(accession: str) -> str:
    """GEO FTP directory stem: GSE193581 -> GSE193nnn/GSE193581."""
    stem = accession[:-3] + "nnn"
    return f"{config.GEO_FTP}/series/{stem}/{accession}"


def list_directory(url: str) -> list[str]:
    """File names in an Apache-style directory listing."""
    html = request("GET", url.rstrip("/") + "/").text
    names = re.findall(r'href="([^"?/][^"]*)"', html)
    return [n for n in names if not n.startswith(("http", "/", "?"))]


def parse_series_matrix_metadata(path: Path) -> tuple[dict[str, list[str]], pd.DataFrame]:
    """Parse ``!Series_*`` and ``!Sample_*`` header lines of a series matrix file."""
    series: dict[str, list[str]] = {}
    sample_rows: list[tuple[str, list[str]]] = []
    opener = gzip.open if str(path).endswith(".gz") else open
    with opener(path, "rt", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            if line.startswith("!series_matrix_table_begin"):
                break
            if not line.startswith("!"):
                continue
            key, _, rest = line.rstrip("\n").partition("\t")
            vals = [v.strip().strip('"') for v in rest.split("\t")] if rest else []
            key = key.lstrip("!")
            if key.startswith("Series_"):
                series.setdefault(key, []).extend(vals)
            elif key.startswith("Sample_"):
                sample_rows.append((key, vals))
    # Sample_characteristics_ch1 repeats: keep each row, labelled by its "tag: value" prefix.
    cols: dict[str, list[str]] = {}
    for key, vals in sample_rows:
        name = key
        if key.startswith("Sample_characteristics"):
            m = re.match(r"([^:]+):", vals[0]) if vals else None
            name = "characteristic_" + (m.group(1).strip().replace(" ", "_") if m else str(len(cols)))
            vals = [v.split(":", 1)[1].strip() if ":" in v else v for v in vals]
        base, i = name, 2
        while name in cols:
            name, i = f"{base}_{i}", i + 1
        cols[name] = vals
    n = max((len(v) for v in cols.values()), default=0)
    meta = pd.DataFrame({k: v + [None] * (n - len(v)) for k, v in cols.items()})
    return series, meta


def fetch_series(accession: str, force: bool = False, supplementary: bool = True) -> str:
    info = config.GEO_DATASETS[accession]
    out_dir = config.DATA_RAW / accession
    base = series_dir_url(accession)
    files: list[Path] = []

    matrix_files = [n for n in list_directory(base + "/matrix") if n.endswith("series_matrix.txt.gz")]
    for name in matrix_files:
        files.append(download(f"{base}/matrix/{name}", out_dir / name, force=force)["path"])
    soft = f"{accession}_family.soft.gz"
    files.append(download(f"{base}/soft/{soft}", out_dir / soft, force=force)["path"])

    suppl_names: list[str] = []
    if supplementary:
        try:
            suppl_names = list_directory(base + "/suppl")
        except Exception as exc:  # no supplementary directory
            log_decision("data gap", f"{accession}: no supplementary directory", str(exc))
        for name in suppl_names:
            files.append(download(f"{base}/suppl/{name}", out_dir / "suppl" / name, force=force)["path"])

    series, meta = parse_series_matrix_metadata(next(p for p in files if p.name.endswith("series_matrix.txt.gz")))
    meta_path = out_dir / f"{accession}_sample_metadata.tsv"
    meta.to_csv(meta_path, sep="\t", index=False)
    files.append(meta_path)

    platform = ", ".join(sorted(set(series.get("Series_platform_id", [])))) or info["platform"]
    write_provenance(
        accession,
        build_record(
            source="NCBI GEO",
            accession=accession,
            url=f"{config.GEO_QUERY}?acc={accession}",
            sample_count=len(meta),
            modality=info["modality"],
            platform=f"{info['platform']} [{platform}]",
            license=LICENSE,
            raw_files=[str(p.relative_to(out_dir)).replace("\\", "/") for p in files],
            checksums=checksums_for(files, out_dir),
            notes=info["notes"],
            series_title=(series.get("Series_title") or [""])[0],
            series_summary=" ".join(series.get("Series_summary", []))[:1500],
            pubmed_ids=series.get("Series_pubmed_id", []),
            supplementary_files=suppl_names,
            sample_metadata_table=str(meta_path.relative_to(config.ROOT)).replace("\\", "/"),
        ),
    )
    return accession


def verify_gsm(gsm: str = config.GEO_VERIFY_SAMPLE, parent: str = "GSE193581") -> str:
    """Determine whether ``gsm`` is standalone or part of ``parent``; log the finding."""
    text = request(
        "GET", config.GEO_QUERY,
        params={"acc": gsm, "targ": "self", "form": "text", "view": "brief"},
    ).text.replace("\r", "")
    series_ids = re.findall(r"^!Sample_series_id = (GSE\d+)", text, flags=re.M)
    title = (re.findall(r"^!Sample_title = (.*)$", text, flags=re.M) or [""])[0]
    source = (re.findall(r"^!Sample_source_name_ch1 = (.*)$", text, flags=re.M) or [""])[0]
    platform = (re.findall(r"^!Sample_platform_id = (.*)$", text, flags=re.M) or [""])[0]
    in_parent = parent in series_ids
    if in_parent:
        verdict = f"{gsm} is a sample within {parent} (series: {', '.join(series_ids)}); it is NOT an independent dataset."
    elif series_ids:
        verdict = f"{gsm} belongs to {', '.join(series_ids)} and is NOT part of {parent}; treat as a separate cohort."
    else:
        verdict = f"Could not determine series membership of {gsm}."
    log_decision("verification", f"{gsm} verification", verdict)
    write_provenance(
        f"{gsm}_verification",
        build_record(
            source="NCBI GEO",
            accession=gsm,
            url=f"{config.GEO_QUERY}?acc={gsm}",
            sample_count=1,
            modality="verification",
            platform=platform or "n/a",
            license=LICENSE,
            notes=verdict,
            parent_series=series_ids,
            is_part_of_gse193581=in_parent,
            sample_title=title,
            sample_source=source,
        ),
    )
    return f"{gsm}_verification"


def geo_search(term: str = "anaplastic thyroid cancer", retmax: int = 500) -> str:
    """ESearch on db=gds and enumerate all hits with metadata."""
    res = ncbi_get("esearch.fcgi", {"db": "gds", "term": term, "retmax": retmax, "retmode": "json"}, as_json=True)["esearchresult"]
    ids = res.get("idlist", [])
    records: list[dict[str, Any]] = []
    for i in range(0, len(ids), 100):
        summ = ncbi_get("esummary.fcgi", {"db": "gds", "id": ",".join(ids[i:i + 100]), "retmode": "json"}, as_json=True)["result"]
        for uid in summ.get("uids", []):
            r = summ[uid]
            records.append({
                "uid": uid,
                "accession": r.get("accession"),
                "entry_type": r.get("entrytype"),
                "gds_type": r.get("gdstype"),
                "title": r.get("title"),
                "summary": r.get("summary"),
                "taxon": r.get("taxon"),
                "n_samples": r.get("n_samples"),
                "platform": r.get("gpl"),
                "pubmed_ids": r.get("pubmedids"),
                "pdat": r.get("pdat"),
            })
    write_provenance(
        "geo_search_results",
        build_record(
            source="NCBI GEO DataSets (esearch, db=gds)",
            accession=f"query: {term}",
            url=f"{config.NCBI_EUTILS}/esearch.fcgi?db=gds&term={term.replace(' ', '+')}",
            sample_count=len(records),
            modality="dataset enumeration",
            platform="NCBI E-utilities",
            license=LICENSE,
            notes=f"All GDS hits for '{term}' (accessions + metadata); {res.get('count', 0)} total hits.",
            query=term,
            total_hits=int(res.get("count", 0)),
            results=records,
        ),
    )
    return "geo_search_results"


def run(force: bool = False, supplementary: bool = True, **_: Any) -> list[str]:
    names = [fetch_series(acc, force=force, supplementary=supplementary) for acc in config.GEO_DATASETS]
    names.append(verify_gsm())
    names.append(geo_search())
    return names
