# Local validation — 2026-09-11

This branch is a local-review release. No Frappe Cloud or production ERPNext deployment was performed.

## Passed

- Fresh app installation on an isolated Frappe version-16 site, Python 3.14.5, with outgoing email muted.
- `bench --site esign.localhost run-tests --app nesscale_sign`: **42 tests passed**. Includes sequential/parallel signing, template workflows, reference-document triggers, token expiry, consent, source tampering, retryable completion, unrelated-user access and audit protections.
- Optional pyHanko 0.36.2 PDF seal: a disposable self-signed local certificate produced a signature verified as intact, valid and trusted against that explicit test trust root. This does not establish public certificate trust.
- `npm test`: **8 tests passed** for CSRF/session handling, readable server errors, upload limits and URL/date handling.
- `npm run build`: successful production assets, approximately 149 KB gzip main JavaScript plus the separately loaded PDF worker.
- `ruff check nesscale_sign` and `git diff --check`: clean.
- Frontend dependency audit: no reported vulnerabilities at validation time.
- Real local Frappe HTTP smoke check: signing HTML and compiled JavaScript/CSS returned HTTP 200.
- Chrome preview: document register, document detail, PDF rendering, typed signature, explicit consent and completion/download flow with fictional records. Screenshots show this preview.

## Limits

The backend site has Frappe installed, not ERPNext. Actual ERPNext permissions, Frappe Drive selection, outgoing-email delivery, production workers, backups, TLS, certificate provisioning and Frappe Cloud installation still require staging validation. Reference integration tests use local test DocTypes. No external timestamp authority was called. Load testing, independent security review and jurisdiction-specific legal review have not been performed.

The isolated test database used MariaDB 12.3.3, which Frappe warned is newer than its tested 11.8 version. Use the database version supported by your Frappe hosting environment.

PDF finalization was exercised directly and through the worker entrypoint; a complete live queue-delivery test remains for staging. The in-memory design preview simulates API behavior and resets on restart; it is not production storage.

## Feature restoration follow-up

Chrome verified dark/light switching, the shared home logo on the signer screen, all field-type controls, uploaded-signature mode, and saving edits back to the same template ID. Added regression coverage for repeat-field grouping/limits, explicit expiry and read-only prefill. Administrative Desk screens remain preserved but are not simulated by the local preview.
