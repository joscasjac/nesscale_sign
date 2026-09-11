# Changelog

## 0.2.0 — local review

- Rename the public workspace to Open E-Sign ERPNext, preserving upstream attribution and internal app identifiers.
- Publish a complete Vue frontend and reproducible Vite build; add document register, preparation, recipient signing, detail and setup screens.
- Add a separate loopback-only design preview with fictional documents.
- Enforce token expiry for reads, explicit consent, read-only field protections, signature-image validation, source file permissions and field bounds.
- Remove signer credentials from normal API responses and restrict standalone evidence records.
- Snapshot/hash originals on send; protect sent documents and audit deletion; serialize signing/audit operations.
- Move PDF finalization to a retryable worker; include completion events and hashes in completion evidence.
- Add optional certificate-based service seals; expose honest configuration status.
- Attach completed artifacts to the selected ERP record.
- Add regression tests and installation/API/security documentation.

Not deployed. Independent security review and production-readiness checks remain required.

### Feature restoration and identity
- Restored uploaded signatures, dark appearance, all field types, repeat/duplicate fields and signing inbox.
- Added template editing, duplicate/archive actions, recipient mappings, automation controls, expiry and activity overview.
- Unified the document-signature logo and home navigation.
- Fixed read-only prefills and explicit expiry being dropped during creation.
