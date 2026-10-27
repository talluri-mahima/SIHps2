# Submission build checklist — 28 October 2026, IST

Goal: a reproducible end-to-end prototype with actual OCR and verification functions, explicit source/rule uncertainty, authorized users, durable evidence and a measured demonstration. This is not a declaration of production certification or access to government systems.

## Ordered work and acceptance

| Step | Work | Working delivery gate |
|---|---|---|
| 1 | Freeze two application contexts, supported documents and source-backed rules | Every enabled check has applicability, inputs, evidence and safe missing-data behavior |
| 2 | Configure environment and integrations without exposing secrets | Readiness screen shows tested / configured / unavailable accurately |
| 3 | Persistent database, private files/object store, schema upgrades | Restart preserves users, evidence, evaluations and audit; older data upgrades |
| 4 | Real user authentication and role assignments | Applicant cannot review; unassigned officer and cross-tenant access denied; demo shortcuts visibly segregated |
| 5 | Native PDF + CPU OCR, isolated derived-page processing | Actual scanned PDF produces source-linked facts; unclear/unsupported input abstains |
| 6 | General document field candidates and correction | Varied labels supported; original text and coordinates retained; critical facts require confirmation |
| 7 | Signature checks and authorized-source workflows | Integrity/trust/availability remain separate; unavailable source never becomes verified |
| 8 | ScopeGuard and Hestia evidence reconciliation | Correct-floor, wrong-floor, unknown-scope, exact-ID and lien cases pass independent expected outcomes |
| 9 | Rectification, re-evaluation, confirmed-only PDF/JSON reports | Replacement preserves history and blocks stale exports; reviewer confirmation is traceable |
| 10 | Adversarial tests and measured document evaluation | Raw counts, misses, abstentions, runtime and tested scope recorded; software tests separated from accuracy |
| 11 | Deployment and backup demo | Fresh setup, browser journey, persistent restart and offline fallback work on submission hardware |
| 12 | Submission package | Screens/video match build; no unmeasured percentages, live-API claims or autonomous approval claims |

## User-owned dependencies

- Target: 28 October, 10 AM IST; user indicated 10–11 AM. Demo runs on the local laptop with internet and free services; paid APIs are deferred.
- No service accounts or authorized issuer credentials currently supplied. Local OCR/database/login do not require paid accounts. Do not send passwords/API secrets in chat.
- Four public institutional PDFs have been collected locally for development. Independent labels, permission for any training and a held-out institutional set remain outstanding. Synthetic fixtures prove behavior, not real-world accuracy.
- Authorized AICTE / issuer API documentation, sandbox credentials and permitted use, if available. There is no assumed universal AICTE/bank verification API.
- A named policy reviewer for the enabled handbook subset and academic-year amendments.

## Connection policy

Use actual services for OCR, identity, storage and databases that we can provision and test. Government/issuer adapters are live only with authorized documented access. Record manual attestations as manual, demo responses as mock, and unavailable sources as unavailable. Do not sacrifice access isolation, provenance, unknown handling or human review for a broader feature list.

Progress is recorded in code, tests and integration readiness; a checked box alone does not establish a working connection.
