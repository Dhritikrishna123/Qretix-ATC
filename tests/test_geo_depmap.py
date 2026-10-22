import pandas as pd

from src.data_acquisition.depmap_fetcher import (
    build_dependency_table, normalise, release_sort_key, resolve_release, select_atc_models,
)
from src.data_acquisition.geo_fetcher import series_dir_url


def test_series_dir_url():
    assert series_dir_url("GSE193581").endswith("/series/GSE193nnn/GSE193581")
    assert series_dir_url("GSE76039").endswith("/series/GSE76nnn/GSE76039")


def test_release_resolution_picks_latest_complete():
    from src.data_acquisition.depmap_fetcher import FILES
    rows = [("DepMap Public 24Q2", f) for f in FILES] + [("DepMap Public 25Q3", f) for f in FILES[:2]]
    rel, _ = resolve_release(pd.DataFrame(rows, columns=["release", "filename"]))
    assert rel == "DepMap Public 24Q2"
    assert release_sort_key("DepMap Public 25Q3") > release_sort_key("DepMap Public 24Q4")


def _models():
    return pd.DataFrame({
        "ModelID": ["ACH-1", "ACH-2", "ACH-3", "ACH-4", "ACH-5"],
        "CellLineName": ["8505C", "CAL-62", "ARO", "SomeLine", "KTC-2"],
        "StrippedCellLineName": ["8505C", "CAL62", "ARO", "SOMELINE", "KTC2"],
        "OncotreeLineage": ["Thyroid", "Thyroid", "Thyroid", "Thyroid", "Thyroid"],
        "OncotreeSubtype": ["Anaplastic Thyroid Cancer"] * 4 + ["Thyroid"],
    })


def test_select_atc_models_authenticated_and_exclusions():
    keep, drop = select_atc_models(_models())
    assert set(keep["CellLineName"]) == {"8505C", "CAL-62", "KTC-2"}
    reasons = dict(zip(drop["CellLineName"], drop["exclusion_reason"]))
    assert "contaminated" in reasons["ARO"]
    assert "not in authenticated" in reasons["SomeLine"]


def test_build_dependency_table_maps_ids():
    class U:
        def from_entrez(self, e): return {"673": "ENSG00000157764"}.get(str(e))
        def from_symbol(self, s): return None
    ge = pd.DataFrame({"ModelID": ["ACH-1", "ACH-9"], "BRAF (673)": [-1.2, 0.1], "FOO (1)": [0.0, 0.0]})
    keep, _ = select_atc_models(_models())
    dep = build_dependency_table(ge, keep, U())
    assert set(dep["model_id"]) == {"ACH-1"}
    braf = dep[dep["hgnc_symbol"] == "BRAF"].iloc[0]
    assert braf["ensembl_gene_id"] == "ENSG00000157764" and braf["chronos_gene_effect"] == -1.2
    assert normalise("CAL-62") == "CAL62"

def test_depmap_blocked_page_becomes_documented_gap(tmp_path, monkeypatch):
    from src import config
    from src.data_acquisition import depmap_fetcher as d
    from src import decisions, provenance

    class Resp:
        headers = {"content-type": "text/html"}
        text = "<!DOCTYPE html><title>DepMap - Verification</title>"

    monkeypatch.setattr(config, "DATA_RAW", tmp_path / "raw")
    monkeypatch.setattr(config, "DATA_PROVENANCE", tmp_path / "prov")
    monkeypatch.setattr(config, "DOCS", tmp_path / "docs")
    monkeypatch.setattr(config, "DECISIONS_LOG", tmp_path / "docs" / "decisions_log.md")
    monkeypatch.setattr(d, "request", lambda *a, **k: Resp())
    assert d.run() == ["DepMap"]
    rec = provenance.load_provenance(tmp_path / "prov" / "DepMap.json")
    assert rec["status"] == "manual_approval_required"
    assert "DepMap not auto-downloadable" in (tmp_path / "docs" / "decisions_log.md").read_text()


def test_depmap_renamed_files_are_found(tmp_path):
    from src.data_acquisition.depmap_fetcher import find_local
    (tmp_path / "OmicsCNGeneWGS.csv").write_text("x")
    (tmp_path / "OmicsExpressionTPMLogp1HumanProteinCodingGenes.csv").write_text("x")
    assert find_local(tmp_path, "OmicsCNGene.csv").name == "OmicsCNGeneWGS.csv"
    assert find_local(tmp_path, "OmicsExpressionProteinCodingGenesTPMLogp1.csv").name.startswith("OmicsExpressionTPMLogp1")
    assert find_local(tmp_path, "Model.csv") is None
