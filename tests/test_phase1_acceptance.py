"""End-to-end acceptance tests verifying 100% compliance with Phase 1 specification."""
import json
import pandas as pd
from pathlib import Path
from src import config, gene_universe, provenance


def test_gene_universe_acceptance():
    assert config.GENE_UNIVERSE_PATH.exists(), "gene_universe.parquet must exist"
    gu = pd.read_parquet(config.GENE_UNIVERSE_PATH)
    assert len(gu) >= config.MIN_GENES_IN_UNIVERSE, f"Gene universe has {len(gu)} (< 19,000)"
    assert gu["ensembl_gene_id"].is_unique, "ensembl_gene_id must be unique"
    for col in ["ensembl_gene_id", "symbol", "uniprot_id", "entrez_id"]:
        assert col in gu.columns
        assert gu[col].notna().mean() >= 0.85, f"Coverage for {col} is below 85%"


def test_depmap_dependency_csv_acceptance():
    dep_csv = config.DATA_PROCESSED / "depmap_atc_dependency.csv"
    assert dep_csv.exists(), "depmap_atc_dependency.csv must exist"
    dep = pd.read_csv(dep_csv)
    assert len(dep) >= 50000, f"depmap_atc_dependency has only {len(dep)} rows"
    
    expected_cols = {
        "model_id", "cell_line", "ensembl_gene_id", "hgnc_symbol",
        "entrez_id", "chronos_gene_effect", "platform", "batch"
    }
    assert expected_cols.issubset(set(dep.columns)), f"Missing columns: {expected_cols - set(dep.columns)}"
    
    # Assert zero contaminated lines
    cell_lines = set(dep["cell_line"].dropna())
    contaminated = cell_lines.intersection(config.CONTAMINATED_ATC_LINES)
    assert not contaminated, f"Contaminated cell lines present: {contaminated}"
    
    # Assert only authenticated ATC lines are present
    norm_lines = {c.replace("-", "").replace(" ", "").upper() for c in cell_lines}
    assert norm_lines.issubset(config.AUTHENTICATED_ATC_LINES)
    assert len(cell_lines) >= 5, f"Expected at least 5 authenticated ATC lines, got {len(cell_lines)}"


def test_provenance_schema_compliance():
    records = provenance.iter_provenance()
    assert len(records) >= 20, f"Expected >= 20 provenance records, found {len(records)}"
    
    required_datasets = {
        "gene_universe", "GSE193581", "GSE76039", "GSM7030310_verification",
        "geo_search_results", "DepMap", "STRING", "UniProt", "Reactome",
        "GeneOntology", "OpenTargets", "ChEMBL", "ENCODE", "GDC_TCGA-THCA",
        "PubMed_ATC", "ClinicalTrials"
    }
    present = {name for name, _ in records}
    missing = required_datasets - present
    assert not missing, f"Missing required provenance files: {missing}"
    
    for name, rec in records:
        problems = provenance.validate_record(rec)
        assert not problems, f"provenance/{name}.json failed schema: {problems}"


def test_documentation_acceptance():
    assert config.DATASET_INVENTORY.exists()
    assert config.DATASET_INVENTORY.stat().st_size > 500
    inv_text = config.DATASET_INVENTORY.read_text(encoding="utf-8")
    assert "| Dataset |" in inv_text
    assert "## Data gaps" in inv_text

    assert config.DECISIONS_LOG.exists()
    assert config.DECISIONS_LOG.stat().st_size > 500
    dec_text = config.DECISIONS_LOG.read_text(encoding="utf-8")
    assert "COSMIC" in dec_text
    assert "DrugBank" in dec_text
    assert "TCGA-THCA" in dec_text


def test_phase_isolation_acceptance():
    # Phase 1 rule: no features or labels may be created yet
    for d in [config.FEATURES_DIR, config.LABELS_DIR]:
        stray = [p.name for p in d.glob("*") if p.name != ".gitkeep"]
        assert not stray, f"{d.name}/ is not empty in Phase 1: {stray}"


def test_raw_data_integrity():
    # Critical raw data files existence and non-zero size
    gse193581_tar = config.DATA_RAW / "GSE193581" / "suppl" / "GSE193581_RAW.tar"
    assert gse193581_tar.exists() and gse193581_tar.stat().st_size > 150 * 1024 * 1024
    
    pubmed = config.LITERATURE / "atc_pubmed_corpus.json"
    assert pubmed.exists() and pubmed.stat().st_size > 1024 * 1024
    with open(pubmed, encoding="utf-8") as fh:
        atc_corpus = json.load(fh)["articles"]
    assert len(atc_corpus) >= 2000
    # Every article must have publication date
    with_date = sum(1 for a in atc_corpus if a.get("publication_date"))
    assert with_date == len(atc_corpus)

    trials = config.LITERATURE / "atc_clinical_trials.json"
    assert trials.exists() and trials.stat().st_size > 10 * 1024
    with open(trials, encoding="utf-8") as fh:
        ct_data = json.load(fh)["studies"]
    assert len(ct_data) >= 50
    with_start = sum(1 for t in ct_data if t.get("study_start_date"))
    assert with_start == len(ct_data)
