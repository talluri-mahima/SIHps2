# Delivery status · milestone 0.1

The original product plan remains the target. This is the first runnable foundation, not a completed product MVP or a declaration that formal gates G0–G6 passed.

| Planned gate | Current state | Outstanding evidence |
|---|---|---|
| G0 policy/context/data freeze | BLOCKED for regulated release | Authoritative full PS, policy owner sign-off, dated handbook/amendment sources and independent labels |
| G1 secure platform | PARTIAL | Local access/session/versioning/jobs implemented; OIDC, PostgreSQL RLS, migrations, private managed objects, mandatory scanner and transactional outbox deployment remain |
| G2 extraction | PARTIAL | Working native labelled-PDF extraction/page boxes; general schemas, OCR, calibrated confidence and independent accuracy set pending |
| G3 reconciliation | PARTIAL | Real deterministic scope/finance/date checks and input manifests; signed approved rule packs, expanded classes and independent golden suite pending |
| G4 review/export | PARTIAL | Working confirmation/response/staleness/history/JSON export; production governance, signed/PDF export and richer rectification UX pending |
| G5 verification/recovery | PARTIAL | Mock/manual source observations and bounded durable extraction jobs; live source contracts, signature validation, OS sandbox, full outage/restore exercise pending |
| G6 release/accuracy | NOT PASSED | Foundation tests and browser smoke are engineering checks; sealed held-out benchmark, real-data pilot, load/recovery, accessibility audit and policy/security acceptance pending |

## Next implementation order

1. Introduce versioned migrations and a tested PostgreSQL profile with least-privilege RLS and OIDC; remove persona shortcuts from that profile.
2. Build quarantine scanning and isolated page-derivative/OCR workers; enforce transport/resource budgets and a managed object store.
3. Freeze independently labelled document families and a sealed test split before broad extraction tuning.
4. Add governed, source-cited rule publication and amendment conflict handling; numeric regulatory thresholds remain disabled until reviewed.
5. Extend rectification links across evaluations, formal source-check entities/history, signature trust tests and immutable report attestations.
6. Run the frozen accuracy protocol, usability/accessibility checks, failure/recovery and release capacity tests.

Development sessions, sample documents and runtime evidence are ignored by Git. No reported test count represents real-world model accuracy. Source-mode labels and unknown results must survive future work.
