"""Step 1.3 — ENCODE: normal thyroid H3K27ac / ATAC-seq reference. ATC absence is logged explicitly."""
from __future__ import annotations

import json
from typing import Any

from src import config
from src.decisions import log_decision
from src.http_utils import download, get_json
from src.provenance import build_record, checksums_for, write_provenance

HEADERS = {"Accept": "application/json"}
FIELDS = ["accession", "assay_title", "target.label", "biosample_ontology.term_name", "description",
          "files.accession", "files.href", "files.file_format", "files.output_type", "files.assembly",
          "files.status", "files.file_size"]


def search(**params: Any) -> dict[str, Any]:
    q: list[tuple[str, str]] = [("type", "Experiment"), ("status", "released"), ("format", "json"), ("limit", "all")]
    q += [("field", f) for f in FIELDS]
    q += list(params.items())  # type: ignore[arg-type]
    return get_json(f"{config.ENCODE_BASE}/search/", params=q, headers=HEADERS)


def pick_reference_files(experiments: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Peak files (GRCh38) of H3K27ac ChIP-seq / ATAC-seq on normal thyroid."""
    picked = []
    for e in experiments:
        assay = e.get("assay_title", "")
        target = (e.get("target") or {}).get("label", "")
        if not (assay == "ATAC-seq" or (assay == "Histone ChIP-seq" and target == "H3K27ac")):
            continue
        for f in e.get("files", []):
            if (f.get("file_format") == "bed" and f.get("assembly") == "GRCh38"
                    and f.get("status") == "released" and "peaks" in f.get("output_type", "")):
                picked.append({"experiment": e["accession"], "assay": assay, "target": target,
                               "file": f["accession"], "href": f["href"], "output_type": f["output_type"],
                               "size": f.get("file_size")})
    return picked


def run(force: bool = False, **_: Any) -> list[str]:
    out_dir = config.DATA_RAW / "ENCODE"
    out_dir.mkdir(parents=True, exist_ok=True)
    atc_hits = search(searchTerm="anaplastic thyroid").get("@graph", [])
    thyroid = search(**{"biosample_ontology.term_name": "thyroid gland"}).get("@graph", [])
    files = pick_reference_files(thyroid)

    downloaded = []
    for f in files:
        downloaded.append(download(config.ENCODE_BASE + f["href"], out_dir / f"{f['file']}.bed.gz", force=force)["path"])
    (out_dir / "thyroid_experiments.json").write_text(json.dumps(thyroid, indent=1), encoding="utf-8")
    (out_dir / "selected_files.json").write_text(json.dumps(files, indent=1), encoding="utf-8")
    manifest = [out_dir / "thyroid_experiments.json", out_dir / "selected_files.json"] + downloaded

    log_decision(
        "data finding", "ENCODE has no ATC biosamples",
        f"Search for 'anaplastic thyroid' returned {len(atc_hits)} released experiments; "
        f"{len(thyroid)} normal thyroid-gland experiments found, {len(files)} H3K27ac/ATAC peak files downloaded as reference.",
    )
    write_provenance("ENCODE", build_record(
        source="ENCODE Project", accession="biosample: thyroid gland", url=f"{config.ENCODE_BASE}/search/",
        sample_count=len(thyroid), modality="epigenomics (H3K27ac ChIP-seq, ATAC-seq; normal thyroid reference)",
        platform="ENCODE portal", license="ENCODE data use policy (open, unrestricted after release)",
        raw_files=[p.name for p in manifest], checksums=checksums_for(manifest, out_dir),
        notes=f"No ATC biosamples (hits: {len(atc_hits)}) — absence logged. Normal thyroid reference only; never ATC evidence.",
        atc_experiments_found=len(atc_hits), reference_files=len(files),
    ))
    return ["ENCODE"]
