# Decisions Log

Data gaps, deviations and judgement calls made while building QRETIX-ATC. Entries are appended automatically by the pipeline and can be edited by hand.

### GSM7030310 verification

- **Category:** verification
- **Date:** 2026-10-22
- **Detail:** GSM7030310 belongs to GSE224719, GSE224721 and is NOT part of GSE193581; treat as a separate cohort.

### depmap failed

- **Category:** resolved (was acquisition failure)
- **Date:** 2026-10-22
- **Detail:** RESOLVED: DepMap files API served a bot-check page; the 5 CSVs were downloaded manually into data/raw/DepMap/ and ingested (7 authenticated ATC lines). Original error: Step 1.4: Error tokenizing data. C error: Expected 1 fields in line 6, saw 2

### geo failed

- **Category:** resolved (was acquisition failure)
- **Date:** 2026-10-22
- **Detail:** RESOLVED: GEO FTP dropped the 189 MB GSE193581_RAW.tar mid-transfer; download() now resumes via HTTP Range and the archive was fully fetched and unpacked (23 samples). Original error: Step 1.1: ('Connection broken: IncompleteRead(155132472 bytes read, 33785288 more expected)', IncompleteRead(155132472 bytes read, 33785288 more expected))

### cBioPortal study thca_gatci_cellrep_2024 unavailable

- **Category:** resolved (was data gap)
- **Date:** 2026-10-22
- **Detail:** RESOLVED: the plan's study ID does not exist; the real study is thyroid_gatci_2024 (190 ATC), mapped and downloaded from cBioPortal DataHub. Original error: API lookup failed: 404 Client Error: Not Found for url: https://www.cbioportal.org/api/studies/thca_gatci_cellrep_2024

### cBioPortal study thca_mskcc_2016 unavailable

- **Category:** resolved (was data gap)
- **Date:** 2026-10-22
- **Detail:** RESOLVED: the plan's study ID does not exist; the real study is thyroid_mskcc_2016 (117 samples: 33 ATC + 84 PDTC), mapped and downloaded. Original error: API lookup failed: 404 Client Error: Not Found for url: https://www.cbioportal.org/api/studies/thca_mskcc_2016

### AACR GENIE ATC search failed

- **Category:** data gap
- **Date:** 2026-10-22
- **Detail:** genie_public is not hosted on the public cBioPortal instance (the original 404). AACR GENIE is distributed via Synapse (syn7222066) after registration and data-use acceptance, so it needs manual access. Impact: no ATC cases from GENIE; potential GENIE/GATCI/MSKCC overlap is moot until it is obtained.

### TCGA-THCA is a PTC reference, not ATC evidence

- **Category:** data caveat
- **Date:** 2026-10-22
- **Detail:** TCGA-THCA contains no ATC cases (all differentiated thyroid carcinoma, predominantly PTC). It is stored only as a 'differentiated thyroid baseline' for ATC-vs-DTC differential features and must never be treated as ATC-specific evidence.

### encode failed

- **Category:** resolved (was acquisition failure)
- **Date:** 2026-10-22
- **Detail:** RESOLVED: ENCODE /search/ returns HTTP 404 for zero hits; this is now treated as an empty result (see 'ENCODE has no ATC biosamples'). Original error: Step 1.3: 404 Client Error: Not Found for url: https://www.encodeproject.org/search/?type=Experiment&status=released&format=json&limit=all&field=accession&field=assay_title&field=target.label&field=biosample_ontology.term_name&field=description&field=files.accession&field=files.href&field=files.file_format&field=files.output_type&field=files.assembly&field=files.status&field=files.file_size&searchTerm=anaplastic+thyroid

### PRIDE PXD030304 unavailable

- **Category:** resolved (was data gap)
- **Date:** 2026-10-22
- **Detail:** RESOLVED: files endpoint changed to /projects/{acc}/files; metadata and file listing retrieved. Original error: Expecting value: line 1 column 1 (char 0)

### PRIDE PXD063991 unavailable

- **Category:** resolved (was data gap)
- **Date:** 2026-10-22
- **Detail:** RESOLVED: files endpoint changed to /projects/{acc}/files; metadata and file listing retrieved. Original error: Expecting value: line 1 column 1 (char 0)

### chembl failed

- **Category:** resolved (was acquisition failure)
- **Date:** 2026-10-22
- **Detail:** RESOLVED: NaN/float handling bug fixed; candidate lookups now run concurrently (103 candidates). Original error: Step 1.5: 'float' object has no attribute 'split'

### COSMIC not acquired (manual approval required)

- **Category:** data gap
- **Date:** 2026-10-22
- **Detail:** Cancer Gene Census requires licence acceptance; cannot be auto-accessed. Flagged as a provenance gap. Impact: Novelty checklist item 4 (COSMIC CGC thyroid) and Phase 4 hard negatives (Cancer Gene Census) will use an alternative or be logged as a gap.

### DisGeNET not acquired (manual approval required)

- **Category:** data gap
- **Date:** 2026-10-22
- **Detail:** Requires registration/API key; flagged as a gap. Impact: Novelty checklist item 2 (DisGeNET ATC) will be logged as a gap; Open Targets used instead.

### DrugBank not acquired (manual approval required)

- **Category:** data gap
- **Date:** 2026-10-22
- **Detail:** Licensed resource; cannot be auto-accessed. ChEMBL + Open Targets used for druggability/pharmacology. Impact: Druggability tiers rely on Open Targets tractability + ChEMBL.

### BioGRID not acquired (skipped)

- **Category:** data gap
- **Date:** 2026-10-22
- **Detail:** Skipped (API key required). STRING + Reactome provide sufficient PPI coverage. Impact: PPI features use STRING (score >= 400) + Reactome only.

### Authenticated ATC lines absent from DepMap

- **Category:** data gap
- **Date:** 2026-10-22
- **Detail:** ACT1, C643, HTH7, HTH83, KAT18, KTC2, KTC3, OCUT1, SW1736, T238 are not in DepMap Public (manually supplied); 7 authenticated ATC lines available.

### DepMap ATC-labelled lines excluded

- **Category:** data cleaning
- **Date:** 2026-10-22
- **Detail:** HOTHC (ATC-labelled in DepMap but not in authenticated ATC list); KMH-2 (ATC-labelled in DepMap but not in authenticated ATC list); CCLF_THYR_0003_T (ATC-labelled in DepMap but not in authenticated ATC list); CCLF_THYR_0004_T (ATC-labelled in DepMap but not in authenticated ATC list); CCLF_THYR_0005_T (ATC-labelled in DepMap but not in authenticated ATC list); CCLF_THYR_0001_T (ATC-labelled in DepMap but not in authenticated ATC list)

### ENCODE has no ATC biosamples

- **Category:** data finding
- **Date:** 2026-10-22
- **Detail:** Search for 'anaplastic thyroid' returned 0 released experiments; 75 normal thyroid-gland experiments found, 31 H3K27ac/ATAC peak files downloaded as reference.

### PRIDE PXD030304 proteomics sparsity

- **Category:** data finding
- **Date:** 2026-10-23
- **Detail:** 287 files listed; 0 quantitation-style tables downloaded (sparse ATC proteomics expected).

### PRIDE PXD063991 proteomics sparsity

- **Category:** data finding
- **Date:** 2026-10-23
- **Detail:** 35 files listed; 1 quantitation-style tables downloaded (sparse ATC proteomics expected).

### PRIDE PXD063991 is not ATC proteomics

- **Category:** data finding
- **Date:** 2026-10-23
- **Detail:** PXD063991 is a yeast (TKO standard) column-comparison benchmark, so the accession listed in the plan carries no thyroid/ATC data. Only its metadata and sample key were retained; no ATC proteomics is usable from it.

### PRIDE PXD030304 is a pan-cancer cell-line atlas

- **Category:** data finding
- **Date:** 2026-10-23
- **Detail:** PXD030304 (ProCan-DepMapSanger, 949 cell lines) is not ATC-specific; ATC-line coverage must be checked via cell-line names in its sample metadata. Large raw/quant files were not downloaded; the file listing is stored for provenance.

### Genomics modalities absent from cBioPortal ATC studies

- **Category:** data gap
- **Date:** 2026-10-23
- **Detail:** Plan expects structural variants for thyroid_gatci_2024 and expression z-scores for thyroid_mskcc_2016. The study packages ship neither (GATCI: mutations, CNA, clinical, gene panel matrix only; MSKCC: mutations, CNA, segments, SV, timeline, clinical, but no mRNA file). ATC transcriptomics therefore comes from GSE76039 (bulk, 20 ATC) and GSE193581 (scRNA-seq).

### GSE193581 contains 32 samples

- **Category:** data finding
- **Date:** 2026-10-23
- **Detail:** 23 single-cell patient samples (10 ATC, 7 PTC, 6 adjacent normal, per the plan) plus 9 bulk ATC cell-line RNA-seq samples (RSEM). Per-patient UMI files unpacked under data/raw/GSE193581/samples/; the cell-line samples are in the series supplementary files.
