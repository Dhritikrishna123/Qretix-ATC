from src.data_acquisition.chembl_fetcher import candidate_symbols
from src.data_acquisition.clinicaltrials_fetcher import parse_study
from src.data_acquisition.pubmed_fetcher import parse_articles
from src.docs_builder import render_inventory
from src.pipeline import execution_order

PUBMED_XML = b"""<PubmedArticleSet>
<PubmedArticle><MedlineCitation><PMID>111</PMID><Article>
 <Journal><Title>J Test</Title><JournalIssue><PubDate><Year>2016</Year><Month>Mar</Month><Day>04</Day></PubDate></JournalIssue></Journal>
 <ArticleTitle>BRAF in ATC</ArticleTitle>
 <Abstract><AbstractText>Anaplastic <i>thyroid</i> cancer.</AbstractText></Abstract>
 <AuthorList><Author><AffiliationInfo><Affiliation>Lab A</Affiliation></AffiliationInfo></Author>
 <Author><AffiliationInfo><Affiliation>Lab B</Affiliation></AffiliationInfo></Author></AuthorList>
 <PublicationTypeList><PublicationType>Journal Article</PublicationType></PublicationTypeList>
</Article><MeshHeadingList><MeshHeading><DescriptorName>Thyroid Carcinoma, Anaplastic</DescriptorName></MeshHeading></MeshHeadingList>
</MedlineCitation></PubmedArticle>
<PubmedArticle><MedlineCitation><PMID>222</PMID><Article>
 <Journal><Title>J Two</Title><JournalIssue><PubDate><MedlineDate>2012 Jan-Feb</MedlineDate></PubDate></JournalIssue></Journal>
 <ArticleTitle>t</ArticleTitle></Article></MedlineCitation></PubmedArticle>
<PubmedArticle><MedlineCitation><PMID>333</PMID><Article>
 <ArticleDate><Year>2020</Year><Month>7</Month><Day>9</Day></ArticleDate>
 <Journal><Title>J Three</Title><JournalIssue><PubDate><Year>2021</Year></PubDate></JournalIssue></Journal>
 <ArticleTitle>e</ArticleTitle></Article></MedlineCitation></PubmedArticle>
</PubmedArticleSet>"""


def test_pubmed_parsing_dates_and_fields():
    a, b, c = parse_articles(PUBMED_XML)
    assert (a["pmid"], a["publication_date"], a["date_precision"]) == ("111", "2016-03-04", "day")
    assert a["abstract"] == "Anaplastic thyroid cancer."
    assert a["mesh"] == ["Thyroid Carcinoma, Anaplastic"]
    assert (a["first_author_affiliation"], a["last_author_affiliation"]) == ("Lab A", "Lab B")
    assert (b["publication_date"], b["date_precision"]) == ("2012", "year")
    assert (c["publication_date"], c["date_precision"]) == ("2020-07-09", "day")  # ArticleDate preferred


def test_clinical_trial_parsing():
    s = {"protocolSection": {
        "identificationModule": {"nctId": "NCT1", "briefTitle": "T"},
        "statusModule": {"overallStatus": "COMPLETED", "startDateStruct": {"date": "2018-05"}},
        "designModule": {"phases": ["PHASE2"]},
        "armsInterventionsModule": {"interventions": [{"name": "Dabrafenib", "type": "DRUG"}]},
    }}
    r = parse_study(s)
    assert r["nct_id"] == "NCT1" and r["study_start_date"] == "2018-05" and r["phase"] == ["PHASE2"]
    assert r["interventions"][0]["name"] == "Dabrafenib"


def test_candidate_symbols_include_drivers_deduped():
    syms = candidate_symbols()
    assert "BRAF" in syms and len(syms) == len(set(syms))


def test_execution_order_and_inventory_render(tmp_path, monkeypatch):
    assert execution_order([1]) == [1]
    from src import config
    monkeypatch.setattr(config, "DATA_PROVENANCE", tmp_path)
    from src.provenance import build_record, write_provenance
    write_provenance("COSMIC", build_record(source="COSMIC", accession="n/a", url="u", modality="m", platform="p",
                                            license="l", notes="needs licence", status="manual_approval_required"))
    md = render_inventory()
    assert "`COSMIC`" in md and "GAP - manual approval" in md and "## Data gaps" in md
