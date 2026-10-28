# Real document evaluation: first collection

Four institution-published PDFs were downloaded on 28 October 2026 into the ignored `.data/public-documents/` directory. The source URLs, retrieval timestamps, byte counts and SHA-256 hashes are in `reports/public-document-sources.json`. The originals are not committed or sent to a cloud provider. Publication is not issuer authentication; reuse/training permission has not been established.

## Initial baseline result

The first collection had 39 pages: TSM occupancy (4), TSM fire licence (1), MES mandatory disclosure (28), BIT Sindri 2026–27 EoA (6). All pages contain some native text, which does not establish that their text layers are accurate or complete. The original 0.2 extractor returned **zero structured field candidates on all four documents** and routed them to manual extraction. This was a coverage failure; subsequent changes must be measured separately. The synthetic development result must not be presented as a real-document benchmark.

## Current provisional evaluation

Version 0.3 adds source-grounded building/floor narrative patterns, approval metadata and ambiguous-table abstention. A fifth PDF, a four-page EoA from a different institution, was collected separately. Parser hashes were frozen before visual inspection of that institution's labels. `fixtures/real-document-labels.json` and `reports/real-document-check.json` record 12 selected expected values: 11 exact matches, one wrong embedded-text institution name, no missed selected values and 10 matches to the labelled source regions. Unscored metadata is listed separately. The handwritten validity date and unlinked building scope remain abstained. Labels are provisional assistant visual labels, not independently validated human ground truth; the data is too small to support representative accuracy claims.

The real public fire-page OCR comparison recovered the expected institution spelling. Its existing fields stayed unchanged and unconfirmed. A reviewer must compare the original and explicitly record a correction. OCR still makes errors, especially on handwriting; a high recognition score cannot certify a date or authenticity.

The live download of an institution-linked fire PDF returned HTML and was rejected by intake; the source manifest records failure. A cached web representation described a payment receipt. This observation motivated a synthetic negative control, not a verified allegation about the institution or a locally measured PDF case. Receipt-page detection now blocks such pages from supporting building/fire scope even when their facts are manually confirmed.

Visual inspection of the TSM first pages confirms material layout differences: a narrative certificate with a small approval table, and a fire licence with inline floor notation and handwritten dates. The website's document label alone does not establish the legal type of each page or the covered building. A bundle must be classified and linked page by page. Existing colon-labelled extraction is insufficient for these layouts.

## Curation and delivery sequence

1. Preserve these originals and their hashes. Record source availability and permission separately from document validity. Never combine unrelated institutions into one real application.
2. Label exact page regions for document type, building identity, covered floors, issuing authority, issue/expiry dates and applicability. Mark absent, ambiguous, illegible and not applicable separately. Keep handwritten numeric dates unconfirmed; do not guess their interpretation.
3. Have a second person independently review the labels. Disagreements are adjudicated against the page, with a reason. Labelled fields are evaluation truth, not proof that the underlying claim is authentic.
4. Collect additional institutions and reserve whole institutions/layout families as an untouched test split **before** tuning extraction. These four documents are development material only. Avoid splitting pages from the same document across train/test.
5. Implement page-level document segmentation, label/value and table association, inline floor notation and narrative evidence candidates. Detect weak text layers and offer rendered-page OCR comparison. Preserve exact source boxes and recognition method. Abstain on ambiguous building linkage and dates.
6. Measure field precision, recall, exact match, abstention and false-supported findings; report denominators and break down native, scanned, handwritten and mixed bundles. Measure page citation correctness, reviewer correction time and latency separately. A model score is not an authenticity probability.
7. Release a demo only after an end-to-end real-document exercise: upload, preview, source-linked extraction or manual entry, officer confirmation, explicit source-verification status, evaluation and report. An unsupported field remains unresolved. Issuer API integrations remain disconnected until authorized access exists.

The implementation is currently an evidence workflow with local OCR and conservative extraction, not a custom-trained or validated AICTE model. Fine-tuning is not required for tomorrow's demo. Reliable source-linked candidates, honest abstention and reproducible evaluation take priority; fine-tuning requires a permitted, labelled corpus and a measured benefit over the baseline.

## Reproduce

Run `.venv\\Scripts\\python.exe scripts/collect_public_documents.py`, then `.venv\\Scripts\\python.exe scripts/inspect_public_documents.py` from the repository folder. Network access is needed only for acquisition. Reports contain coverage metadata, not extracted personal information. Source availability and PDF content may change; hashes distinguish revisions.
