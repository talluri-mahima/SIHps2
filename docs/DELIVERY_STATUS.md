# Delivery status · milestone 0.2 local prototype

The original product plan remains the target. This is the first runnable foundation, not a completed product MVP or a declaration that formal gates G0–G6 passed.

## Local additions since 0.1

Versioned SQLite migrations, bounded derived-page processing, local RapidOCR, source-linked manual transcription, offline PDF signature checks, safe QR decoding without following links, immutable verification observations, frozen JSON/PDF reports, local password sign-in, backup tooling and integration readiness are implemented. Windows Defender scanning is optional and only reported connected after an actual successful provider observation. The explicit PaddleOCR adapter uses a separate environment and locally provisioned model files; consult its execution reports before claiming it is enabled or benchmarked.

Real-document acquisition is reproducible: four institution-published PDFs, 39 pages, stored locally with source hashes. Initial automatic critical-field coverage was zero. Layout changes now expose source-linked review hints and unique same-row label/value associations; these are not independent accuracy results. See `REAL_DOCUMENT_EVALUATION.md`, `PADDLE_OCR.md` and the current reports. Training permission, independent labels and a held-out test set remain open.

| Planned gate | Current state | Outstanding evidence |
|---|---|---|
| G0 policy/context/data freeze | BLOCKED for regulated release | Authoritative full PS, policy owner sign-off, dated handbook/amendment sources and independent labels |
| G1 secure platform | PARTIAL | Local access/session/versioning/jobs and migrations implemented; OIDC, PostgreSQL RLS, private managed objects, mandatory scanner deployment and transactional outbox remain |
| G2 extraction | PARTIAL | Native text, local OCR, source boxes, manual facts and layout hints; broader schemas, text-layer quality detection, calibration and independent accuracy set pending |
| G3 reconciliation | PARTIAL | Real deterministic scope/finance/date checks and input manifests; signed approved rule packs, expanded classes and independent golden suite pending |
| G4 review/export | PARTIAL | Confirmation/response/staleness, historical API and frozen JSON/PDF export implemented; production governance, signed report attestation and richer rectification UX pending |
| G5 verification/recovery | PARTIAL | Mock/manual source observations, offline signature checks, QR inspection, backup tool and bounded durable jobs; live source contracts, revocation evidence, OS sandbox and full outage/restore exercise pending |
| G6 release/accuracy | NOT PASSED | Foundation tests and browser smoke are engineering checks; sealed held-out benchmark, real-data pilot, load/recovery, accessibility audit and policy/security acceptance pending |

## Next implementation order

1. Introduce versioned migrations and a tested PostgreSQL profile with least-privilege RLS and OIDC; remove persona shortcuts from that profile.
2. Build quarantine scanning and isolated page-derivative/OCR workers; enforce transport/resource budgets and a managed object store.
3. Freeze independently labelled document families and a sealed test split before broad extraction tuning.
4. Add governed, source-cited rule publication and amendment conflict handling; numeric regulatory thresholds remain disabled until reviewed.
5. Extend rectification links across evaluations, formal source-check entities/history, signature trust tests and immutable report attestations.
6. Run the frozen accuracy protocol, usability/accessibility checks, failure/recovery and release capacity tests.

Development sessions, sample documents and runtime evidence are ignored by Git. No reported test count represents real-world model accuracy. Source-mode labels and unknown results must survive future work.
