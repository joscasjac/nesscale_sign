# API and ERP integration

Use a Frappe API key/secret for a dedicated user with the minimum appropriate signing and source-record permissions. Put credentials on your server, never in frontend JavaScript. Standard Frappe authentication and CSRF rules apply.

Authenticated calls use `/api/method/nesscale_sign.api.<module>.<method>`.

## Create from an existing private PDF

POST `envelope.create_adhoc` with:

```json
{
  "data": {
    "title": "Service agreement",
    "pdf_file": "/private/files/agreement.pdf",
    "routing_type": "Sequential",
    "source_doctype": "Quotation",
    "source_name": "SAL-QTN-2026-00001",
    "signers": [{"signer_name": "Alex", "signer_email": "alex@example.com", "role_key": "client", "signing_order": 1}],
    "fields": [{"field_key": "signature", "field_type": "Signature", "label": "Signature", "signer_role": "client", "page": 1, "pos_x": 0.1, "pos_y": 0.8, "width": 0.3, "height": 0.08, "required": 1}]
  }
}
```

The caller must be allowed to read the File and write the optional source record. Fields use normalized page coordinates with a top-left origin. PDF limits: 15 MB, 100 pages; flatten existing form widgets before upload. Draft creation does not send email.

## Send and retrieve

- POST `envelope.send_envelope` with `{"name":"NS-ENV-..."}`: freezes original and sends invitations.
- POST `envelope.get_envelope` with the name: retrieves status, fields and audit, with signer tokens removed.
- GET `envelope.download_signed?name=...`: completed PDF.
- GET `envelope.download_certificate?name=...`: completion evidence.
- POST `envelope.retry_completion`: retries failed processing without collecting signatures again.
- POST `envelope.void_envelope`: voids an outstanding request.

`signing.submit` is token-scoped and POST-only. Supply values, a valid signature image where required, and `consent: true`. The final signer receives `processing`; poll context/status for completion. The long worker produces PDFs after the signing transaction commits. Failures preserve collected signatures and are visible to the sender.

This fork does not promise a versioned third-party webhook delivery service. Same-site ERP integration uses existing Frappe document triggers and attachment linkage; external consumers can poll the authenticated status endpoint.

Completed signers can download evidence with GET `signing.download_certificate?token=...`. The token is validated and the envelope must be completed.
