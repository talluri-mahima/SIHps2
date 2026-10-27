# Real document evaluation: first collection

Four institution-published PDFs were downloaded on 28 October 2026 into the ignored `.data/public-documents/` directory. The source URLs, retrieval timestamps, byte counts and SHA-256 hashes are in `reports/public-document-sources.json`. The originals are not committed or sent to a cloud provider. Publication is not issuer authentication; reuse/training permission has not been established.

## Observed result

The first collection has 39 pages: TSM occupancy (4), TSM fire licence (1), MES mandatory disclosure (28), BIT Sindri 2026–27 EoA (6). All pages contain some native text, which does not establish that their text layers are accurate or complete. The current conservative extractor returned **zero structured field candidates on all four documents**, and correctly routed them to manual extraction. See `reports/public-layout-coverage.json` for the actual run. This is a coverage failure, not evidence of real-world accuracy. The synthetic development result must not be presented as a real-document benchmark.

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
