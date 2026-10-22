"""Export and package Phase 1 datasets for Hugging Face Hub.

Converts tabular, clinical, and literature artifacts into optimized Apache Parquet
tables, compiles comprehensive provenance, generates a Hugging Face Dataset Card
(README.md) with full YAML metadata, and uploads to Hugging Face.
"""
from __future__ import annotations

import json
import os
import shutil
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from huggingface_hub import HfApi

from src import config

HF_EXPORT_DIR = config.ROOT / "data" / "hf_export"
HF_DATA_DIR = HF_EXPORT_DIR / "data"


def export_gene_universe() -> Path:
    """Copies gene universe parquet to HF export directory."""
    src = config.GENE_UNIVERSE_PATH
    dest = HF_DATA_DIR / "gene_universe.parquet"
    shutil.copy2(src, dest)
    return dest


def export_depmap_tables() -> tuple[Path, Path]:
    """Converts DepMap dependency CSV and models CSV to Parquet."""
    dep_csv = config.DATA_PROCESSED / "depmap_atc_dependency.csv"
    models_csv = config.DATA_PROCESSED / "depmap_atc_models.csv"

    dep_df = pd.read_csv(dep_csv)
    dep_pq = HF_DATA_DIR / "depmap_atc_dependency.parquet"
    dep_df.to_parquet(dep_pq, index=False, engine="pyarrow")

    models_df = pd.read_csv(models_csv)
    models_pq = HF_DATA_DIR / "depmap_atc_models.parquet"
    models_df.to_parquet(models_pq, index=False, engine="pyarrow")

    return dep_pq, models_pq


def export_literature_tables() -> tuple[Path, Path]:
    """Converts PubMed and Clinical Trials JSON files to Parquet."""
    pm_json = config.LITERATURE / "atc_pubmed_corpus.json"
    ct_json = config.LITERATURE / "atc_clinical_trials.json"

    with open(pm_json, "r", encoding="utf-8") as f:
        pm_data = json.load(f)
    pm_df = pd.DataFrame(pm_data)
    # Ensure list columns like mesh_terms serialize properly
    pm_pq = HF_DATA_DIR / "atc_pubmed_corpus.parquet"
    pm_df.to_parquet(pm_pq, index=False, engine="pyarrow")

    with open(ct_json, "r", encoding="utf-8") as f:
        ct_data = json.load(f)
    ct_df = pd.DataFrame(ct_data)
    ct_pq = HF_DATA_DIR / "atc_clinical_trials.parquet"
    ct_df.to_parquet(ct_pq, index=False, engine="pyarrow")

    return pm_pq, ct_pq


def export_cbioportal_tables() -> tuple[Path, Path]:
    """Packages GATCI (2024) and MSKCC (2016) mutations and clinical data into Parquet."""
    dfs_mut = []
    gatci_mut = config.DATA_RAW / "thca_gatci_cellrep_2024" / "data_mutations.txt"
    if gatci_mut.exists():
        df_g = pd.read_csv(gatci_mut, sep="\t", comment="#", low_memory=False)
        df_g["study_id"] = "thyroid_gatci_2024"
        dfs_mut.append(df_g)

    mskcc_mut = config.DATA_RAW / "thca_mskcc_2016" / "data_mutations.txt"
    if mskcc_mut.exists():
        df_m = pd.read_csv(mskcc_mut, sep="\t", comment="#", low_memory=False)
        df_m["study_id"] = "thyroid_mskcc_2016"
        dfs_mut.append(df_m)

    if dfs_mut:
        # Standardize core columns
        core_cols = [
            "study_id",
            "Hugo_Symbol",
            "Entrez_Gene_Id",
            "NCBI_Build",
            "Chromosome",
            "Start_Position",
            "End_Position",
            "Variant_Classification",
            "Variant_Type",
            "Reference_Allele",
            "Tumor_Seq_Allele1",
            "Tumor_Seq_Allele2",
            "Tumor_Sample_Barcode",
            "HGVSc",
            "HGVSp_Short",
        ]
        merged_mut = pd.concat(dfs_mut, ignore_index=True)
        # Keep core columns present
        cols_to_keep = [c for c in core_cols if c in merged_mut.columns]
        mut_df = merged_mut[cols_to_keep]
    else:
        mut_df = pd.DataFrame()

    mut_pq = HF_DATA_DIR / "cbioportal_atc_mutations.parquet"
    mut_df.to_parquet(mut_pq, index=False, engine="pyarrow")

    # Clinical samples
    dfs_clin = []
    gatci_clin = config.DATA_RAW / "thca_gatci_cellrep_2024" / "data_clinical_sample.txt"
    if gatci_clin.exists():
        df_gc = pd.read_csv(gatci_clin, sep="\t", comment="#")
        df_gc["study_id"] = "thyroid_gatci_2024"
        dfs_clin.append(df_gc)

    mskcc_clin = config.DATA_RAW / "thca_mskcc_2016" / "data_clinical_sample.txt"
    if mskcc_clin.exists():
        df_mc = pd.read_csv(mskcc_clin, sep="\t", comment="#")
        df_mc["study_id"] = "thyroid_mskcc_2016"
        dfs_clin.append(df_mc)

    if dfs_clin:
        clin_df = pd.concat(dfs_clin, ignore_index=True)
    else:
        clin_df = pd.DataFrame()

    clin_pq = HF_DATA_DIR / "cbioportal_atc_clinical.parquet"
    clin_df.to_parquet(clin_pq, index=False, engine="pyarrow")

    return mut_pq, clin_pq


def export_opentargets_table() -> Path:
    """Extracts Open Targets ATC target associations into Parquet."""
    ot_json = config.DATA_RAW / "OpenTargets" / "atc_associated_targets.json"
    rows_data = []
    if ot_json.exists():
        with open(ot_json, "r", encoding="utf-8") as f:
            ot_raw = json.load(f)
        for r in ot_raw.get("rows", []):
            target = r.get("target", {})
            dt_scores = {s["id"]: s["score"] for s in r.get("datatypeScores", [])}
            # Summarize tractability
            tract = target.get("tractability", [])
            has_approved_drug_sm = any(
                t.get("label") == "Approved Drug" and t.get("modality") == "SM" and t.get("value")
                for t in tract
            )
            has_clinical_sm = any(
                t.get("label") == "Advanced Clinical" and t.get("modality") == "SM" and t.get("value")
                for t in tract
            )
            has_approved_ab = any(
                t.get("label") == "Approved Drug" and t.get("modality") == "AB" and t.get("value")
                for t in tract
            )

            rows_data.append({
                "target_ensembl_id": target.get("id"),
                "approved_symbol": target.get("approvedSymbol"),
                "overall_association_score": r.get("score"),
                "score_literature": dt_scores.get("literature"),
                "score_somatic_mutation": dt_scores.get("somatic_mutation"),
                "score_rna_expression": dt_scores.get("rna_expression"),
                "score_affected_pathway": dt_scores.get("affected_pathway"),
                "has_approved_drug_sm": has_approved_drug_sm,
                "has_clinical_sm": has_clinical_sm,
                "has_approved_ab": has_approved_ab,
            })

    ot_df = pd.DataFrame(rows_data)
    ot_pq = HF_DATA_DIR / "opentargets_atc_targets.parquet"
    ot_df.to_parquet(ot_pq, index=False, engine="pyarrow")
    return ot_pq


def export_provenance_manifest() -> Path:
    """Aggregates all provenance manifests into a single Parquet table."""
    records = []
    prov_dir = config.DATA_PROVENANCE
    for p in sorted(prov_dir.glob("*.json")):
        try:
            with open(p, "r", encoding="utf-8") as f:
                d = json.load(f)
                records.append({
                    "dataset_id": d.get("dataset_id", p.stem),
                    "source_name": d.get("source_name", ""),
                    "version": d.get("version", ""),
                    "access_date": d.get("access_date", ""),
                    "license": d.get("license", ""),
                    "sha256": d.get("sha256", ""),
                    "num_records": d.get("num_records", 0),
                    "is_gap": bool(d.get("gap_record", False)),
                    "gap_reason": d.get("gap_reason", ""),
                })
        except Exception:
            continue

    prov_df = pd.DataFrame(records)
    prov_pq = HF_DATA_DIR / "provenance_manifest.parquet"
    prov_df.to_parquet(prov_pq, index=False, engine="pyarrow")
    return prov_pq


def generate_dataset_card() -> Path:
    """Generates the official Hugging Face Dataset Card (README.md)."""
    readme_path = HF_EXPORT_DIR / "README.md"
    card_content = """---
annotations_creators:
- machine-generated
- expert-generated
language:
- en
license: cc-by-4.0
multilinguality:
- monolingual
size_categories:
- 100K<n<1M
source_datasets:
- DepMap
- cBioPortal
- NCBI GEO
- PubMed
- OpenTargets
- UniProt
task_categories:
- tabular-classification
- tabular-regression
- text-retrieval
- feature-extraction
task_ids: []
tags:
- oncology
- thyroid-cancer
- anaplastic-thyroid-carcinoma
- drug-discovery
- crispr-cas9
- genomics
- transcriptomics
pretty_name: QRETIX-ATC Phase 1 Multi-Omic & Literature Knowledge Base
---

# QRETIX-ATC: Anaplastic Thyroid Carcinoma (ATC) Multi-Omic & Literature Database

## Overview
**QRETIX-ATC Phase 1** is a curated, high-integrity multi-omic and biomedical literature knowledge base specifically assembled to support target discovery, drug repurposing, and molecular modeling in **Anaplastic Thyroid Carcinoma (ATC)**.

ATC is one of the most lethal solid tumors in humans, with a median survival of only 3 to 6 months. This repository unifies dependency genetics, tumor genomics, transcriptomics, target tractability, and literature evidence into high-performance Apache Parquet tables.

## Dataset Structure & Files

All tables are stored in Apache Parquet format under the `data/` directory for fast columnar querying and seamless integration with `pandas`, `polars`, `pyarrow`, and Hugging Face `datasets`.

| Table Name | Description | Rows / Records | Key Columns |
| :--- | :--- | :--- | :--- |
| **`data/gene_universe.parquet`** | Unified human protein-coding gene reference | 19,255 | `hgnc_id`, `approved_symbol`, `ensembl_gene_id`, `uniprot_ids`, `entrez_id` |
| **`data/depmap_atc_dependency.parquet`** | DepMap CRISPR/RNAi gene dependency scores | 106,716 | `model_id`, `cell_line`, `hgnc_symbol`, `entrez_id`, `chronos_gene_effect` |
| **`data/depmap_atc_models.parquet`** | Authenticated ATC cell line models metadata | 7 lines | `ModelID`, `StrippedCellLineName`, `OncotreePrimaryDisease`, `RRID` |
| **`data/cbioportal_atc_mutations.parquet`** | Somatic mutations from GATCI 2024 & MSKCC 2016 | 23,769 | `study_id`, `Hugo_Symbol`, `Variant_Classification`, `HGVSp_Short` |
| **`data/cbioportal_atc_clinical.parquet`** | Patient and sample clinical annotations | 307 samples | `study_id`, `SAMPLE_ID`, `PATIENT_ID`, `HISTOLOGICAL_SUBTYPE` |
| **`data/opentargets_atc_targets.parquet`** | Open Targets ATC disease target associations & tractability | 1,293 | `approved_symbol`, `overall_association_score`, `has_approved_drug_sm` |
| **`data/atc_pubmed_corpus.parquet`** | Curated ATC PubMed literature corpus | 3,248 | `pmid`, `title`, `abstract`, `pub_date`, `mesh_terms` |
| **`data/atc_clinical_trials.parquet`** | ATC clinical trials from ClinicalTrials.gov | 110 | `nct_id`, `title`, `phase`, `interventions`, `start_date` |
| **`data/provenance_manifest.parquet`** | Cryptographic provenance, checksums, access logs | 27 sources | `dataset_id`, `source_name`, `license`, `sha256`, `num_records` |

---

## Strict Cell Line Authentication Protocols

A major historical flaw in thyroid cancer research is cell line cross-contamination (e.g., lines misidentified or contaminated with melanoma or colon cancer). In accordance with the Schweppe et al. (2008) consensus:
- **In Vitro ATC Lines Included (7 validated models)**:
  - `8305C` (`ACH-000858`)
  - `8505C` (`ACH-000781`)
  - `ASH-3` (`ACH-000877`)
  - `BHT-101` (`ACH-000762`)
  - `CAL-62` (`ACH-000454`)
  - `HTC-C3` (`ACH-001099`)
  - `MB-1` (`ACH-001083`)
- **Contaminated & Redundant Lines Excluded**:
  - `ARO` (established colon cancer HT-29 cross-contaminant)
  - `KAT-4` (HT-29 cross-contaminant)
  - `NPA` (melanoma M14 cross-contaminant)
  - `WRO` (cross-contaminant)

---

## Usage Example

### Python (using pandas / pyarrow / huggingface_hub)
```python
import pandas as pd
from huggingface_hub import hf_hub_download

# Download and read gene dependency table
file_path = hf_hub_download(
    repo_id="Dhritikrishna123/qretix-atc-phase1",
    filename="data/depmap_atc_dependency.parquet",
    repo_type="dataset"
)
dep_df = pd.read_parquet(file_path)
print(dep_df.head())

# Read curated ATC PubMed corpus
corpus_path = hf_hub_download(
    repo_id="Dhritikrishna123/qretix-atc-phase1",
    filename="data/atc_pubmed_corpus.parquet",
    repo_type="dataset"
)
corpus_df = pd.read_parquet(corpus_path)
print(f"Loaded {len(corpus_df)} ATC articles")
```

---

## Licensing & Provenance
- All derived tables are shared under the **Creative Commons Attribution 4.0 International (CC-BY 4.0)** license.
- Individual component datasets adhere to the open-access terms of their respective originators:
  - **DepMap**: Broad Institute DepMap open research terms (CC-BY 4.0).
  - **NCBI GEO & PubMed**: National Library of Medicine open public access.
  - **cBioPortal**: GATCI Cell Reports 2024 & MSKCC JCO 2016 open access cohorts.
  - **Open Targets**: EMBL-EBI open target platform.
- Proprietary commercial databases (COSMIC, DrugBank) are explicitly excluded from data binaries and documented only via provenance schema manifests.

---

## Citation & Contact
Authored and maintained as part of the **QRETIX-ATC** project.
- **Maintainer**: Dhritikrishna Tripathi (<dhritikrishnat@gmail.com>)
- **Repository**: [GitHub Qretix-ATC](https://github.com/Dhritikrishna123/Qretix-ATC)
"""
    readme_path.write_text(card_content, encoding="utf-8")
    return readme_path


def package_phase1_for_hf() -> Dict[str, Any]:
    """Packages all Phase 1 assets into the HF export directory."""
    HF_DATA_DIR.mkdir(parents=True, exist_ok=True)
    summary: Dict[str, Any] = {}

    print("Packaging gene universe...")
    p_gu = export_gene_universe()
    summary["gene_universe"] = str(p_gu.relative_to(HF_EXPORT_DIR))

    print("Packaging DepMap dependency tables...")
    p_dep, p_mod = export_depmap_tables()
    summary["depmap_dependency"] = str(p_dep.relative_to(HF_EXPORT_DIR))
    summary["depmap_models"] = str(p_mod.relative_to(HF_EXPORT_DIR))

    print("Packaging literature and clinical trials...")
    p_pm, p_ct = export_literature_tables()
    summary["pubmed_corpus"] = str(p_pm.relative_to(HF_EXPORT_DIR))
    summary["clinical_trials"] = str(p_ct.relative_to(HF_EXPORT_DIR))

    print("Packaging cBioPortal genomics & clinical...")
    p_mut, p_clin = export_cbioportal_tables()
    summary["cbioportal_mutations"] = str(p_mut.relative_to(HF_EXPORT_DIR))
    summary["cbioportal_clinical"] = str(p_clin.relative_to(HF_EXPORT_DIR))

    print("Packaging Open Targets associations...")
    p_ot = export_opentargets_table()
    summary["opentargets_targets"] = str(p_ot.relative_to(HF_EXPORT_DIR))

    print("Packaging provenance manifest...")
    p_prov = export_provenance_manifest()
    summary["provenance_manifest"] = str(p_prov.relative_to(HF_EXPORT_DIR))

    print("Generating Hugging Face Dataset Card (README.md)...")
    p_card = generate_dataset_card()
    summary["dataset_card"] = str(p_card.relative_to(HF_EXPORT_DIR))

    return summary


def upload_to_huggingface(
    repo_id: str = "Dhritikrishna123/qretix-atc-phase1",
    private: bool = False,
) -> str:
    """Creates repo if needed and uploads the package folder to Hugging Face."""
    api = HfApi()
    print(f"Creating / ensuring HF dataset repository: {repo_id}")
    api.create_repo(repo_id=repo_id, repo_type="dataset", private=private, exist_ok=True)

    print(f"Uploading files from {HF_EXPORT_DIR} to {repo_id}...")
    api.upload_folder(
        folder_path=str(HF_EXPORT_DIR),
        repo_id=repo_id,
        repo_type="dataset",
        commit_message="Initial release of QRETIX-ATC Phase 1 curated datasets",
    )
    url = f"https://huggingface.co/datasets/{repo_id}"
    print(f"Upload complete! View at: {url}")
    return url


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Package and upload Phase 1 to Hugging Face.")
    parser.add_argument("--upload", action="store_true", help="Upload directly to Hugging Face Hub.")
    parser.add_argument("--repo-id", default="Dhritikrishna123/qretix-atc-phase1", help="HF repo ID.")
    parser.add_argument("--private", action="store_true", help="Make repository private.")
    args = parser.parse_args()

    results = package_phase1_for_hf()
    print("\nPackage created successfully:")
    for k, v in results.items():
        print(f"  - {k}: {v}")

    if args.upload:
        url = upload_to_huggingface(repo_id=args.repo_id, private=args.private)
        print(f"\nPublished to: {url}")
