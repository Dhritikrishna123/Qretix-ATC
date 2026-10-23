"""Step 1.2 — Genomics (cBioPortal + GDC).

cBioPortal: GATCI 2024 + MSKCC 2016 (datahub study packages), AACR GENIE ATC search.
GDC: TCGA-THCA, labelled strictly as a PTC / differentiated-thyroid REFERENCE — never ATC evidence.
"""
from __future__ import annotations

import tarfile
from pathlib import Path
from typing import Any

from src import config
from src.decisions import log_decision
from src.http_utils import download, get_json, request
from src.provenance import build_record, checksums_for, write_provenance

CBIO_LICENSE = "Open access via cBioPortal (see study citation / publication terms)"
GDC_LICENSE = "GDC open-access data (NCI GDC Data Access Policies)"


CBIO_STUDY_MAP = {
    "thca_gatci_cellrep_2024": "thyroid_gatci_2024",
    "thca_mskcc_2016": "thyroid_mskcc_2016",
}


def fetch_cbio_study(study_id: str, force: bool = False) -> str:
    desc = config.CBIO_STUDIES[study_id]
    remote_id = CBIO_STUDY_MAP.get(study_id, study_id)
    out_dir = config.DATA_RAW / study_id
    try:
        meta = get_json(f"{config.CBIOPORTAL_API}/studies/{remote_id}")
    except Exception as exc:
        log_decision("data gap", f"cBioPortal study {study_id} unavailable", f"API lookup failed for {remote_id}: {exc}")
        write_provenance(study_id, build_record(
            source="cBioPortal", accession=study_id, url=f"{config.CBIOPORTAL_API}/studies/{remote_id}",
            modality="genomics", platform="n/a", license=CBIO_LICENSE, status="not_available",
            notes=f"{desc}: study not found on cBioPortal ({exc}).",
        ))
        return study_id

    tar_path = out_dir / f"{study_id}.tar.gz"
    download(f"{config.CBIOPORTAL_DATAHUB}/{remote_id}.tar.gz", tar_path, force=force)
    extracted: list[Path] = []
    with tarfile.open(tar_path) as tf:
        for member in tf.getmembers():
            if not member.isfile():
                continue
            target = (out_dir / Path(member.name).relative_to(Path(member.name).parts[0])
                      if len(Path(member.name).parts) > 1 else out_dir / member.name)
            target.parent.mkdir(parents=True, exist_ok=True)
            if not target.exists() or force:
                with tf.extractfile(member) as src, open(target, "wb") as dst:  # type: ignore[union-attr]
                    dst.write(src.read())
            extracted.append(target)
    wanted = [p for p in extracted if p.name.startswith(("data_mutations", "data_cna", "data_clinical", "data_sv",
                                                         "data_structural", "data_cna_hg19", "data_expression",
                                                         "data_mrna", "meta_"))]
    wanted = wanted or extracted
    write_provenance(study_id, build_record(
        source="cBioPortal",
        accession=f"{study_id} ({remote_id})",
        url=f"https://www.cbioportal.org/study/summary?id={remote_id}",
        sample_count=meta.get("allSampleCount"),
        modality="genomics (mutations, CNA, structural variants, clinical)",
        platform="Pre-called calls from cBioPortal datahub (not raw VCFs)",
        license=CBIO_LICENSE,
        raw_files=[str(p.relative_to(out_dir)).replace("\\", "/") for p in wanted],
        checksums=checksums_for(wanted, out_dir),
        notes=f"{desc}. Already-processed calls (not raw VCFs). Citation: {meta.get('citation', 'n/a')}",
        study_name=meta.get("name"),
        pmid=meta.get("pmid"),
    ))
    return study_id


def search_genie_atc() -> str:
    """Look for ATC cases in AACR GENIE (OncoTree code THAP) without pulling the full study."""
    name = "AACR_GENIE_ATC"
    try:
        studies = get_json(f"{config.CBIOPORTAL_API}/studies", params={"projection": "ID"}, timeout=120)
        if config.CBIO_GENIE_STUDY not in {s["studyId"] for s in studies}:
            raise LookupError(
                f"study '{config.CBIO_GENIE_STUDY}' is not hosted on the public cBioPortal instance; "
                "AACR GENIE is distributed via Synapse (syn7222066) after registration/data-use acceptance, "
                "so it requires manual access")
        rows = get_json(
            f"{config.CBIOPORTAL_API}/studies/{config.CBIO_GENIE_STUDY}/clinical-data",
            params={"clinicalDataType": "SAMPLE", "attributeId": "ONCOTREE_CODE",
                    "projection": "SUMMARY", "pageSize": 1_000_000},
            timeout=300,
        )
        atc = [r for r in rows if r.get("value") in config.ATC_ONCOTREE_CODES]
        out_dir = config.DATA_RAW / name
        out_dir.mkdir(parents=True, exist_ok=True)
        import json
        path = out_dir / "genie_atc_samples.json"
        path.write_text(json.dumps(atc, indent=2), encoding="utf-8")
        log_decision(
            "data finding", "AACR GENIE ATC case count",
            f"{len(atc)} ATC (OncoTree {sorted(config.ATC_ONCOTREE_CODES)}) samples found among {len(rows)} GENIE samples. "
            "Sample list stored; mutation pull deferred (GENIE data-use terms) — potential overlap with GATCI/MSKCC to be de-duplicated in Phase 2.",
        )
        write_provenance(name, build_record(
            source="cBioPortal (AACR GENIE)", accession=config.CBIO_GENIE_STUDY,
            url=f"https://www.cbioportal.org/study/summary?id={config.CBIO_GENIE_STUDY}",
            sample_count=len(atc), modality="genomics (sample inventory only)",
            platform="AACR GENIE panels", license="AACR Project GENIE data use terms",
            raw_files=[path.name], checksums=checksums_for([path], out_dir),
            notes=f"Searched OncoTree {sorted(config.ATC_ONCOTREE_CODES)}: {len(atc)} ATC samples of {len(rows)}.",
        ))
    except Exception as exc:
        log_decision("data gap", "AACR GENIE ATC search failed", str(exc))
        write_provenance(name, build_record(
            source="cBioPortal (AACR GENIE)", accession=config.CBIO_GENIE_STUDY,
            url=f"{config.CBIOPORTAL_API}/studies/{config.CBIO_GENIE_STUDY}", modality="genomics",
            platform="n/a", license="AACR Project GENIE data use terms", status="not_available",
            notes=f"GENIE ATC search could not be completed: {exc}",
        ))
    return name


def _gdc_files(data_type: str, workflow: str | None = None) -> list[dict[str, Any]]:
    import json
    content = [
        {"op": "in", "content": {"field": "cases.project.project_id", "value": ["TCGA-THCA"]}},
        {"op": "in", "content": {"field": "data_type", "value": [data_type]}},
        {"op": "in", "content": {"field": "access", "value": ["open"]}},
    ]
    if workflow:
        content.append({"op": "in", "content": {"field": "analysis.workflow_type", "value": [workflow]}})
    params = {
        "filters": json.dumps({"op": "and", "content": content}),
        "fields": "file_id,file_name,file_size,md5sum,data_type,analysis.workflow_type,cases.submitter_id",
        "size": 2000, "format": "json",
    }
    return get_json(f"{config.GDC_API}/files", params=params)["data"]["hits"]


def fetch_gdc_thca(force: bool = False, download_data: bool = False, expression: bool = False) -> str:
    """TCGA-THCA manifest (+ optional downloads). Labelled PTC reference, NOT ATC."""
    import json
    name = "GDC_TCGA-THCA"
    out_dir = config.DATA_RAW / name
    out_dir.mkdir(parents=True, exist_ok=True)
    sets = {
        "mutations_maf": _gdc_files("Masked Somatic Mutation"),
        "cnv_segments": _gdc_files("Masked Copy Number Segment"),
        "expression_counts": _gdc_files("Gene Expression Quantification", "STAR - Counts"),
    }
    manifest = out_dir / "manifest.json"
    manifest.write_text(json.dumps(sets, indent=2), encoding="utf-8")
    files = [manifest]
    if download_data:
        for key, hits in sets.items():
            if key == "expression_counts" and not expression:
                continue
            for h in hits:
                dest = out_dir / key / f"{h['file_id']}_{h['file_name']}"
                if dest.exists() and not force:
                    files.append(dest)
                    continue
                for attempt in range(1, 6):
                    try:
                        download(f"{config.GDC_API}/data/{h['file_id']}", dest, force=force)
                        break
                    except Exception:
                        if attempt == 5:
                            raise
                        import time
                        time.sleep(5 * attempt)
                files.append(dest)
    counts = {k: len(v) for k, v in sets.items()}
    log_decision(
        "data caveat", "TCGA-THCA is a PTC reference, not ATC evidence",
        "TCGA-THCA contains no ATC cases (all differentiated thyroid carcinoma, predominantly PTC). "
        "It is stored only as a 'differentiated thyroid baseline' for ATC-vs-DTC differential features "
        "and must never be treated as ATC-specific evidence.",
    )
    write_provenance(name, build_record(
        source="NCI GDC", accession="TCGA-THCA", url="https://portal.gdc.cancer.gov/projects/TCGA-THCA",
        sample_count=max(counts.values()), modality="genomics + transcriptomics (PTC reference)",
        platform="TCGA (STAR counts, masked MAF, masked CNV segments)", license=GDC_LICENSE,
        raw_files=[str(p.relative_to(out_dir)).replace("\\", "/") for p in files[:50]],
        checksums=checksums_for(files[:50], out_dir),
        notes="Labelled as PTC / differentiated-thyroid REFERENCE, NOT ATC. "
              f"Manifest file counts: {counts}. Data downloads: {'yes' if download_data else 'manifest only (use --gdc-download)'}.",
        file_counts=counts, is_atc_evidence=False, downloaded=download_data,
    ))
    return name


def run(force: bool = False, gdc_download: bool = False, **_: Any) -> list[str]:
    names = [fetch_cbio_study(s, force=force) for s in config.CBIO_STUDIES]
    names.append(search_genie_atc())
    names.append(fetch_gdc_thca(force=force, download_data=gdc_download))
    return names
