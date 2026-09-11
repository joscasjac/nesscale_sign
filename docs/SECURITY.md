# Security model and operator setup

This release is for local review. It has not received an independent penetration test or legal review. No claims of SOC 2, ISO 27001, eIDAS qualification, ESIGN/UETA compliance or universal legal enforceability are made.

## What a signature means here

A signer authenticates by possession of a unique email link. Forwarding that link transfers access. This is not government-ID verification or independently verified human identity. Stronger authentication such as OTP/SSO/identity verification remains future work.

The server records explicit consent text/version, signer actions, metadata, and document hashes. The audit chain is application-protected, not external immutable storage: an administrator with database access can rewrite an unanchored chain. Use separately controlled backups or immutable archival storage when your requirements demand administrator-resistant evidence.

## Document integrity

The original PDF is copied and hashed at send time. Finalization refuses a changed original or inconsistent audit chain. Completed PDF bytes are hashed and recorded in the completion record. Read-only signer fields cannot be changed through save-progress. Signing tokens are omitted from ordinary envelope API responses. Sent envelope edits and audit deletion are blocked through normal document APIs.

Completed signers can download their completed document using the original link after signing expiry; expired, voided and declined outstanding requests cannot access the original. Treat completed links as long-lived access credentials. Do not put signing URLs in analytics or support screenshots. Use HTTPS, redacted access logs, and no-referrer policy.

## Certificate-based PDF sealing (optional)

Install the extra into the bench environment:

```sh
./env/bin/pip install -e 'apps/nesscale_sign[sealing]'
```

Set the following **server-side site configuration**, using secret-management procedures appropriate to your host. Never commit real values or expose them to the browser:

| Key | Purpose |
|---|---|
| `esign_pkcs12_path` | Absolute path to an operator-provided PKCS#12 signing certificate/private key file, readable only by the worker account. |
| `esign_pkcs12_password` | Password for that key file. |
| `esign_timestamp_url` | Optional operator-approved timestamp authority endpoint. |
| `esign_require_seal` | Set true to refuse unsealed completion. |

With no certificate and sealing not required, the app clearly reports **Not configured** and produces an unsealed PDF plus evidence record. With a configured certificate, signing errors fail completion rather than silently falling back. Retry from the document page after correcting configuration.

A service seal establishes document integrity under its certificate; it does not turn each participant into a certificate-verified person. PDF-reader trust depends on your certificate chain. A self-signed certificate is suitable for testing, not an automatic trusted identity. Key rotation, certificate expiry monitoring, revocation information and long-term archival validation are operator responsibilities; this release does not implement PAdES-LTA archival renewal.

On Frappe Cloud, verify a supported mechanism for key storage and the optional dependency before enabling sealing. If the host cannot securely provide it, use an external signing/KMS integration rather than copying a key into the public repo.

## Before production

- Run the Frappe regression suite and perform real mail delivery and retry tests on a separate site.
- Test two simultaneous signers, cancelled/expired links, role isolation, large and unusual PDFs, and restore from backup.
- Configure outgoing email, worker/scheduler health monitoring and certificate-expiry monitoring.
- Review document retention, deletion, evidence and identity requirements for your contracts and jurisdictions.
- Restrict the local preview to loopback; never expose it as a production service.

Existing envelopes sent before this fork have no send-time PDF hash; they cannot be safely finalized under the new rule. Void and reissue them after migration. Do not backfill a current hash and pretend it proves the original bytes.

Report security concerns privately to the fork maintainer using GitHub's available private reporting/contact mechanism. Do not attach real signing tokens or customer files to public issues.
