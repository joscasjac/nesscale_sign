<div align="center">
  <img src="nesscale_sign/public/images/logo.svg" alt="Open E-Sign" width="64" />
  <h1>Open E-Sign</h1>
  <p><strong>Build. Send. Sign. Keep the record.</strong></p>
  <p>An open-source document builder and electronic-signature workspace for Frappe and ERPNext.</p>
  <p>
    <a href="#getting-started">Get started</a> ·
    <a href="docs/API.md">API</a> ·
    <a href="integrations/frappe_assistant_core/README.md">Assistant tools</a> ·
    <a href="docs/SECURITY.md">Security</a> ·
    <a href="license.txt">AGPL-3.0</a>
  </p>
</div>

![Open E-Sign structured document builder](docs/images/document-builder.png)

Create a document from blocks or upload a PDF. Add recipients and fillable fields, send it for signature, and download the completed document with its completion certificate included.

Open E-Sign is an independently maintained fork with its own builder, guided signing experience and assistant integration. It runs inside your Frappe site and uses your configured outgoing email account. Screenshots below use fictional local-preview data.

## One workspace, from draft to completion

| Prepare | Send and sign | Keep the record |
| --- | --- | --- |
| Structured text, images, tables and dividers | Sequential or parallel recipients | Signed PDF with certificate pages appended |
| Upload and rearrange existing PDFs | Type, draw or upload a signature | Original-document SHA-256 and audit trail |
| Reusable document templates | Guided required fields and explicit final consent | Completion artifacts attached to ERP records |
| Document variables and `{{` suggestions | Email templates or custom wording | Optional certificate-based PDF sealing |

### Build documents with structure

The full-width builder keeps pages, elements, recipients and properties together. Edit text and table cells directly in the document. Use Heading 1–5, paragraph formatting, colours and spacing controls. Drag blocks to reorder them; place fillable fields on imported PDFs.

- Start from a blank document, an existing PDF, or a reusable template.
- Insert contact and document variables with the toolbar or by typing `{{`.
- Preview resolved variables before sending.
- Create, edit, duplicate, publish and archive templates.
- Revise a sent document while no recipient has signed. Revising invalidates the previous links and creates a new draft to send.

### See what needs attention

![Document dashboard with fictional records](docs/images/documents.png)

Search documents and filter by signing status. Open a record to review recipients, progress, activity and downloads. The **Awaiting my signature** view brings your own pending documents together.

### Guide every signer to the finish

![Guided signing with fields directly on the document](docs/images/signing-inline.png)

Signers review highlighted fields directly on the PDF. Required prefills still need review. After the last required field is completed, the final review opens automatically; consent and **Finish signing** remain explicit.

![Type, draw or upload a signature](docs/images/signing-popup.png)

### Keep the certificate with the document

Every newly completed PDF includes its completion certificate as the final pages. A separate certificate download is also available. When a service seal is configured, the document and certificate pages are combined **before** sealing.

The app captures signing events, consent and an audit trail. A completion certificate is not the same as a cryptographic signature. Sealing is optional and requires your own certificate configuration. See [security and sealing](docs/SECURITY.md) and the [sample completion certificate](docs/examples/completion-certificate.pdf).

## Getting started

### Try the local demo

Use **Node 22.12+**, preferably Node 24:

```sh
git clone --branch codex/open-esign https://github.com/joscasjac/nesscale_sign.git
cd nesscale_sign/frontend
npm ci
npm run preview:local
```

Open [the local preview](http://127.0.0.1:4173/nesscale-sign). **Try signing** opens a fictional document.

The demo uses an in-memory API on port 4174. It sends no email, connects to no ERPNext site, and resets when restarted. Frappe Desk settings are available on an installed site, not in this preview.

### Install on Frappe

Requires **Frappe 16, Python 3.14+, Node 24**, MariaDB, Redis and running Frappe workers/scheduler. ERPNext is optional for standalone signing; linked ERP records require the corresponding app to be installed.

```sh
cd /path/to/frappe-bench
bench get-app --branch codex/open-esign https://github.com/joscasjac/nesscale_sign.git
bench --site YOUR_SITE install-app nesscale_sign
bench --site YOUR_SITE migrate
bench build --app nesscale_sign
```

Open `/nesscale-sign`. Assign `Nesscale Sign User` or `Nesscale Sign Manager` and configure an outgoing **Email Account**. Manage application settings and Email Templates in Frappe Desk.

**Frappe Cloud:** add this repository and the `codex/open-esign` branch to your bench, deploy it, then install the app on your site. Built frontend assets are committed in the repository. Test upgrades on a separate site and follow the [deployment guide](docs/DEPLOYMENT.md).

The internal package name, route and existing role names remain compatible with the original app. The product name is **Open E-Sign**; do not rename the Python package or database DocTypes during installation.

## Assistant tools and API

Nine permission-checked tools integrate with Frappe Assistant Core:

- Inspect the builder format, templates and documents.
- Create a draft from content, a PDF, or a template.
- Update drafts, send invitations, and revise unsigned documents.

Draft creation does not send email. Signature submission remains with the signer. The connector requires the app-discovery patch and enablement described in the [integration guide](integrations/frappe_assistant_core/README.md); installing this app alone does not enable the tools in an existing connector.

For direct integration, see [API examples](docs/API.md).

## Current scope

- Builder documents: up to 20 A4 pages and 200 blocks. Text overflow is rejected rather than clipped.
- PDF uploads: up to 10 files, 15 MB total and 100 pages.
- Supporting email attachments: up to 5 files and 10 MB total.
- Contact selection uses the current Frappe user's permissions. Prefilled recipient details are snapshots.
- No payment collection, product catalogue or video blocks in this iteration.
- No direct Frappe Drive picker; export a PDF and upload it.
- Email-link signing verifies possession of the link. It does not provide independent identity verification or qualified electronic signatures.

## Development

```sh
cd frontend
npm ci
npm run build
npm test
```

The build generates `nesscale_sign/public/frontend/` and the Frappe HTML entrypoint. Edit source files rather than compiled assets.

Run backend tests on an isolated site—they create records:

```sh
bench --site YOUR_TEST_SITE set-config allow_tests true
bench --site YOUR_TEST_SITE run-tests --app nesscale_sign
```

[Contributing](CONTRIBUTING.md) · [Changelog](CHANGELOG.md) · [Validation notes](docs/VALIDATION.md) · [Feature comparison](docs/FEATURES.md)

## License and attribution

Open E-Sign is maintained independently from [Nesscale Sign](https://github.com/bhavesh95863/nesscale_sign), originally created by Nesscale Solutions. Thank you to the upstream contributors for the foundation.

Licensed under [AGPL-3.0](license.txt). Preserve copyright notices and provide corresponding source to users of modified network services as required by the license. The app includes a visible source link. This fork is not endorsed by Nesscale Solutions or Frappe.
