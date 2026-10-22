"""Central configuration: paths, endpoints and constants shared by all Phase 1 modules."""
from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_RAW = ROOT / "data" / "raw"
DATA_PROCESSED = ROOT / "data" / "processed"
DATA_PROVENANCE = ROOT / "data" / "provenance"
LITERATURE = ROOT / "literature"
DOCS = ROOT / "docs"
FEATURES_DIR = ROOT / "features"
LABELS_DIR = ROOT / "labels"

GENE_UNIVERSE_PATH = DATA_PROCESSED / "gene_universe.parquet"
DECISIONS_LOG = DOCS / "decisions_log.md"
DATASET_INVENTORY = DOCS / "dataset_inventory.md"

# --- NCBI (GEO + PubMed E-utilities) ---------------------------------------
NCBI_API_KEY = os.environ.get("NCBI_API_KEY") or None
NCBI_EMAIL = os.environ.get("NCBI_EMAIL", "dhritikrishnat@gmail.com")
NCBI_EUTILS = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
# 3 req/s without a key, 10 req/s with one.
NCBI_MIN_INTERVAL = 0.11 if NCBI_API_KEY else 0.36

USER_AGENT = "Qretix-ATC/0.1 (data-pipeline; +https://github.com/Dhritikrishna123/Qretix-ATC)"

# --- Source endpoints -------------------------------------------------------
HGNC_URL = (
    "https://storage.googleapis.com/public-download-files/hgnc/tsv/tsv/"
    "hgnc_complete_set.txt"
)
GEO_FTP = "https://ftp.ncbi.nlm.nih.gov/geo"
GEO_QUERY = "https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi"
CBIOPORTAL_API = "https://www.cbioportal.org/api"
CBIOPORTAL_DATAHUB = "https://datahub.assets.cbioportal.org"
GDC_API = "https://api.gdc.cancer.gov"
DEPMAP_FILES_API = "https://depmap.org/portal/api/download/files"
STRING_BASE = "https://stringdb-downloads.org/download"
UNIPROT_STREAM = "https://rest.uniprot.org/uniprotkb/stream"
REACTOME_GMT = "https://reactome.org/download/current/ReactomePathways.gmt.zip"
GO_OBO = "https://purl.obolibrary.org/obo/go.obo"
GOA_HUMAN_GAF = "https://current.geneontology.org/annotations/goa_human.gaf.gz"
OPENTARGETS_GQL = "https://api.platform.opentargets.org/api/v4/graphql"
CHEMBL_API = "https://www.ebi.ac.uk/chembl/api/data"
CTGOV_API = "https://clinicaltrials.gov/api/v2/studies"
ENCODE_BASE = "https://www.encodeproject.org"
PRIDE_API = "https://www.ebi.ac.uk/pride/ws/archive/v2"

# --- Domain constants -------------------------------------------------------
ATC_MONDO_ID = "MONDO_0006468"  # Open Targets uses underscore form in GraphQL
ATC_ONCOTREE_CODES = {"THAP"}  # OncoTree: Anaplastic Thyroid Cancer
STRING_MIN_SCORE = 400

# Authenticated ATC lines (normalised: upper-case alphanumerics only).
AUTHENTICATED_ATC_LINES = {
    "8505C", "CAL62", "C643", "SW1736", "BHT101", "8305C", "HTH7", "HTH83",
    "HTCC3", "MB1", "ACT1", "ASH3", "KAT18", "OCUT1", "T238", "KTC2", "KTC3",
}
# Cross-contaminated / misidentified lines (Schweppe et al. 2008).
CONTAMINATED_ATC_LINES = {"ARO", "DRO", "KAT4", "NPA", "FRO"}

GEO_DATASETS = {
    "GSE193581": {
        "modality": "scRNA-seq",
        "platform": "10x Genomics 3' v3",
        "notes": "Lu et al., JCI 2023. 10 ATC, 7 PTC, 6 adjacent normal thyroid.",
    },
    "GSE76039": {
        "modality": "bulk microarray + mutation data",
        "platform": "Affymetrix Human Genome U133 Plus 2.0 (GPL570)",
        "notes": "Landa et al., JCI 2016. 37 PDTC/ATC tumours.",
    },
}
GEO_VERIFY_SAMPLE = "GSM7030310"

CBIO_STUDIES = {
    "thca_gatci_cellrep_2024": "GATCI 2024 ATC cohort (190 tumours)",
    "thca_mskcc_2016": "MSKCC 2016: 33 ATC + 84 PDTC",
}
CBIO_GENIE_STUDY = "genie_public"

PUBMED_ATC_QUERY = '"anaplastic thyroid carcinoma"[tiab] OR "anaplastic thyroid cancer"[tiab]'
PUBMED_THYROID_QUERY = '"thyroid cancer"[tiab] OR "thyroid carcinoma"[tiab]'

PRIDE_ACCESSIONS = ["PXD030304", "PXD063991"]

MIN_GENES_IN_UNIVERSE = 19000


def ensure_dirs() -> None:
    for p in (DATA_RAW, DATA_PROCESSED, DATA_PROVENANCE, LITERATURE, DOCS):
        p.mkdir(parents=True, exist_ok=True)
