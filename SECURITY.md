# Development security boundary

This milestone accepts synthetic documents on a loopback-only development server. Do not deploy it for real institutional evidence.

## Enforced now

Application and object authorization; explicit officer/auditor assignments; rejected cross-tenant access; opaque hashed session tokens; HttpOnly SameSite cookies; expiry and logout revocation; origin/host checks; role checks on every reviewer mutation; strict request fields; upload size/type checks; no user-controlled external URL fetching; bounded parser child process; active-PDF structure checks; immutable evidence versions; critical-fact confirmation; row-version review checks; stale export blocking; hash-linked transactional audit; production startup refusal.

The synthetic demo shortcuts intentionally allow switching personas and automatically assign the known demo officer/auditor to applications created by the synthetic applicant. These are not production provisioning policies. Password login exists for integration development; initial demo accounts have random unrevealed passwords and use local persona sign-in. Rate limiting is in-process and not production-grade.

## Required before release

OIDC/SSO and hardened recovery/session lifecycle; DB migrations and PostgreSQL RLS tested with non-owner roles; OS-level parser network/memory isolation; mandatory malware provider; private object store and encryption/key management; signature trust/revocation validation; retained independent audit copies; controlled rule author/approver workflow; privacy/retention/legal-hold design; source agreements; authorized deployment security review.

Native preview rendering currently happens in the API after parser acceptance; this must move to isolated derivative generation before untrusted real documents are accepted. Multipart transport can spool input before application limits; enforce HTTP/body limits at the server/proxy before production. The local database/global write lock supports one development process, not horizontally scaled operation. Immutable rows/hash chains are not protection against a privileged database/file administrator. File writes and DB commits are not one atomic storage transaction; orphan-object cleanup is pending.

Report issues privately to the repository maintainers through an available private channel. Do not publish real evidence, credentials or exploit sensitive live systems. This file establishes no legal or regulatory compliance certification.
