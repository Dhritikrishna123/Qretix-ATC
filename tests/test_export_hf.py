"""Tests for Hugging Face packaging and export."""
from pathlib import Path
import pandas as pd
import pytest

from src import export_hf, config


def test_package_phase1_for_hf(tmp_path, monkeypatch):
    test_export_dir = tmp_path / "hf_export"
    monkeypatch.setattr(export_hf, "HF_EXPORT_DIR", test_export_dir)
    monkeypatch.setattr(export_hf, "HF_DATA_DIR", test_export_dir / "data")

    res = export_hf.package_phase1_for_hf()

    # Check all expected tables are returned
    expected_keys = [
        "gene_universe",
        "depmap_dependency",
        "depmap_models",
        "pubmed_corpus",
        "clinical_trials",
        "cbioportal_mutations",
        "cbioportal_clinical",
        "opentargets_targets",
        "provenance_manifest",
        "dataset_card",
    ]
    for k in expected_keys:
        assert k in res, f"Missing {k} in summary"
        p = test_export_dir / res[k]
        assert p.exists(), f"File {p} does not exist"
        assert p.stat().st_size > 0, f"File {p} is empty"

    # Verify Parquet content
    dep_df = pd.read_parquet(test_export_dir / res["depmap_dependency"])
    assert len(dep_df) == 106716
    assert "model_id" in dep_df.columns
    assert "hgnc_symbol" in dep_df.columns
    assert "chronos_gene_effect" in dep_df.columns

    models_df = pd.read_parquet(test_export_dir / res["depmap_models"])
    assert len(models_df) == 7
    assert "ModelID" in models_df.columns

    # Verify README Dataset Card YAML header
    readme_text = (test_export_dir / "README.md").read_text(encoding="utf-8")
    assert "license: cc-by-4.0" in readme_text
    assert "pretty_name: QRETIX-ATC" in readme_text
    assert "Strict Cell Line Authentication Protocols" in readme_text
