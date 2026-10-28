# Submission rehearsal — local prototype 0.3

## Start and choose the right case

From the repository directory, run `./scripts/start-prototype.ps1` in PowerShell. It starts a hidden, loopback-only server and verifies its health. Open http://127.0.0.1:8765. Use the named local accounts in ignored `.data/local-access.txt`, or the visibly labelled local demonstration roles. No paid API account is required. Restarting the laptop requires running the launcher again.

Three useful cases are available:

1. **Example Institute of Technology:** five synthetic originals, a missing occupancy floor and a financial lien inconsistency. This is the editable starting demonstration.
2. **ScopeGuard — completed SYNTHETIC rectification:** a recorded clarification, applicant response, replacement certificate, explicit MOCK source observation, newer evaluation and officer-role resolution. All automatic rehearsal actions identify themselves as synthetic in their reasons. This is a software rehearsal, not a real officer's scrutiny.
3. **Public TSM documents — review only, issuer unverified:** two publicly published documents from the same institution. No real application claim was invented. Facts remain unconfirmed and issuer status remains unchecked. This demonstrates real layouts, page navigation, an embedded-text-layer warning and optional local OCR comparison.

The real document case and the synthetic rectification case have deliberately different purposes. Never present the synthetic floor claim or replacement as an actual claim/certificate of TSM.

## Five-minute presenter walkthrough

**0:00–0:40 — Problem and overview.** Explain that a submitted file, a recognized value, an authenticated issuer and applicable evidence scope are different things. Show the workflow overview and current document/fact counts. There is no opaque “overall authenticity percentage.”

**0:40–1:40 — Exact evidence.** Open the Example case, then Evidence and Occupancy. Click the covered-floors fact to highlight its original source. Open Infrastructure: ground/first floor are supported by the accepted documentary scope; second-floor occupancy remains unknown. Unknown does not mean the room is absent, or that the institution is noncompliant.

**1:40–2:50 — Rectification.** Open the completed synthetic case and Findings. Expand Clarification & rectification. Inspect the request, applicant response, old original, replacement version, newer evaluation and reviewed resolution. Source mode remains MOCK. Export the PDF: it carries the resolution history and source-mode limitation.

**2:50–4:10 — Real document processing.** Open the public TSM case. Browse all four occupancy pages with the page selector, including pages without extracted facts. On the fire document, show the warning that embedded OCR text can contain errors. If the alternative OCR observation is present, inspect it; otherwise click “Re-read page 1 with local OCR.” This is a real CPU workload and may take up to roughly two minutes on dense pages. It does not change accepted facts. Review/edit remains an explicit officer action.

**4:10–5:00 — Boundaries and proof.** Open Integrations. Local PaddleOCR and Defender are connected/available according to their real state. AICTE, banks, DigiLocker and issuing authorities are not live integrations. Show the measured reports and explain what remains unvalidated.

## What the evidence supports

- `reports/foundation-gate.json`: automated behavior checks plus a frontend build, with source fingerprints. This is not model accuracy.
- `reports/browser-smoke.json`: the main browser journey; later screenshots are in `reports/screenshots/redesign/`.
- `reports/real-document-check.json`: 12 selected, provisionally visually labelled fields across four PDFs: 11 exact values, one wrong name from embedded text, and 10 matches to the labelled citation regions. Other candidate keys are unscored. This is a tiny development evaluation with no independent human labels; do not turn it into a generalized accuracy percentage.
- `reports/extractor-freeze.json`: parser hashes before inspection of the institution-separated EoA label set. This is not a sealed independently administered benchmark.
- `reports/ocr-provider-rehearsal.json`: two real-page OCR runs with actual latency. Comparing recognized-region counts does not compare accuracy.
- `reports/paddle-upload-rehearsal.json`: the earlier actual login/upload/Defender/PaddleOCR/preview/signature workflow on a synthetic scan.
- `reports/public-ocr-comparison.json`, when present: actual real-page PaddleOCR comparison, with accepted facts unchanged. One phrase check is not representative OCR accuracy.

## Before submitting

1. Keep the laptop awake and plugged in; run the launcher and check the homepage.
2. Rehearse the five-minute route once. Use the recorded OCR observation if a live rerun would consume the presentation window; clearly identify it as a recorded result.
3. Verify the package's `PACKAGE_MANIFEST.json` and current test/CI links.
4. Have a teammate review the provisional field labels against the source PDFs and record disagreements using `fixtures/label-review-template.csv`. Independent validation has not been completed by the assistant.
5. Do not upload private institutional records or the ignored credentials/data folders to GitHub or the submission portal. The packaged source excludes those folders and the downloaded original PDFs.

## Source-backed pitch

Our prototype helps a scrutiny officer establish **which claim is supported, by which document version, on which page, for which building/floor, with what unresolved verification**. The public AICTE Approval Process Handbook describes scrutiny and authenticity/rectification context in section 1.8 and distinguishes building/occupancy/fire evidence in section 6.17. We use that context for draft decision support; we do not claim the executable subset is an AICTE-approved regulatory interpretation.

Primary policy author: AICTE, *Approval Process Handbook 2024–25 to 2026–27*, [government-hosted copy](https://cdnbbsr.s3waas.gov.in/s35938b4d054136e5d59ada6ec9c295d7a/uploads/2025/03/2025031399.pdf). The host is a government mirror, not the AICTE portal. Applicable amendments and policy-owner sign-off remain to be checked before operational use.

Real layout sources: [TSM mandatory disclosures](https://tsm.ac.in/mandatory-disclosure), [BIT Sindri published EoA](https://www.bitsindri.ac.in/wp-content/uploads/2026/04/Extension-of-Approval-EOA-Report-2026-27.pdf), and [BCREC APC published EoA](https://bcrecapc.ac.in/public/pdf/2026-27.PDF). Institutional publication does not independently authenticate the issuer. The source manifest records retrieval hashes and unestablished training permission.

Do not claim “first ever,” “fraud proven,” “government connected,” “production ready,” “independently validated accuracy,” or an SIH win guarantee. The defensible differentiator is visible, versioned evidence reconciliation with human review and measured abstention/error behavior.
