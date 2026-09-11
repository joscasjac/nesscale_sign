# Open E-Sign ERPNext

A document-first signing workspace for Frappe 16 and ERPNext. Prepare an existing PDF, choose recipients, place fields, and keep the completed files with your ERP records.

An independently maintained fork of [Nesscale Sign](https://github.com/bhavesh95863/nesscale_sign) by Nesscale Solutions. AGPL-3.0. The internal app name remains `nesscale_sign` for compatibility.

**Status: local-review release. Not deployed to production.** This is not a claim of DocuSign parity, legal certification, qualified signatures, or independently audited security. Read [security and deployment prerequisites](docs/SECURITY.md) before using real contracts.

![Document register with fictional demo records](docs/images/documents.png)

## What it does

- A clear document register, searchable by title and signing status.
- PDF preparation with recipient roles, drag-to-position fields, and keyboard-editable coordinates and dimensions.
- Sequential or parallel signing, email-link access, explicit electronic-signing consent, and typed/drawn signatures.
- Reusable PDF templates and existing Frappe document-event automation.
- Permission-checked APIs; completed PDF and completion record attached to the selected ERP record.
- Original-PDF snapshots and SHA-256 fingerprints, protected audit records, serialized signing updates, and retryable PDF completion.
- Optional certificate-based PDF sealing with pyHanko. No signing certificate is included. Sealing is visibly reported as **not configured** until an operator configures one.
- Full frontend source, a reproducible build, and a loopback-only local preview with fictional data.

![Signing experience with a fictional document](docs/images/signing.png)

![Document detail and activity](docs/images/document-detail.png)

## Try the design locally

Node 22.12+ (Node 24 recommended):

```sh
git clone --branch codex/open-esign https://github.com/joscasjac/nesscale_sign.git
cd nesscale_sign/frontend
npm ci
npm run preview:local
```

Open **http://127.0.0.1:4173/nesscale-sign**. Use **Try signing** in the preview banner to sign a fictional document and download a generated sample PDF.

This preview uses a separate in-memory server at `127.0.0.1:4174`. It does not connect to ERPNext, send emails, provide cryptographic seals, or persist data after restart. It demonstrates the actual frontend with a simulated API; it is not a substitute for the Frappe backend tests. Desk-only settings require a real Frappe site. The preview service is excluded from the production build.

## Install on a test Frappe site

Requires **Frappe 16, Python 3.14+, Node 24**, MariaDB, Redis and working Frappe workers/scheduler. ERPNext is optional for standalone signing; record links require the referenced DocType to be installed.

```sh
cd /path/to/frappe-bench
bench get-app --branch codex/open-esign https://github.com/joscasjac/nesscale_sign.git
bench --site YOUR_TEST_SITE install-app nesscale_sign
bench --site YOUR_TEST_SITE migrate
bench build --app nesscale_sign
```

Open `/nesscale-sign`. Assign `Nesscale Sign User` or `Nesscale Sign Manager` roles in Frappe. Configure an outgoing **Email Account** for invitations. The app does not supply an email service.

The built frontend is committed for installation on Frappe Cloud; frontend source lives in `frontend/`. Installing requires a bench deployment and a site install. **Do not deploy this local-review branch to a live site without testing and explicit approval.**

## Build and test

```sh
cd frontend
npm ci
npm run build
npm test
```

The build writes `nesscale_sign/public/frontend/` and the Frappe HTML entrypoint. Never hand-edit compiled assets.

On an isolated Frappe site (tests create records):

```sh
bench --site YOUR_TEST_SITE set-config allow_tests true
bench --site YOUR_TEST_SITE run-tests --app nesscale_sign
```

See [API examples](docs/API.md), [security configuration](docs/SECURITY.md), [local validation notes](docs/VALIDATION.md), and [changes](CHANGELOG.md).

## Existing documents and Drive

Document authoring remains in your existing tools. Upload the finished PDF or use a saved template. Optionally enter the source DocType and record name when preparing a document. The sender must have write access to that record. Final PDFs and completion records are attached there.

There is no direct Frappe Drive picker yet. Export/upload a PDF from Drive; the signing app freezes its own copy when sending, so later edits to the working document cannot change the agreement being signed.

## Contributing and license

See [CONTRIBUTING.md](CONTRIBUTING.md). Keep improvements reusable, document migrations, and test permission boundaries. No production keys, personal documents, or real signer data belong in fixtures or screenshots.

Licensed under [AGPL-3.0](license.txt). Preserve upstream attribution and offer corresponding source to network users of modified versions as required by the license. This fork keeps a visible source link in the app. Branding does not imply endorsement by Nesscale Solutions or Frappe.
