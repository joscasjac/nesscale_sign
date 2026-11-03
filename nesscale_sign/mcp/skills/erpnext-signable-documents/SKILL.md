---
name: erpnext-signable-documents
description: Create and manage signable documents, contracts, NDAs, contractor agreements, signature requests and e-sign templates inside ERPNext using Nesscale Sign/Open E-Sign MCP. Use for "make this signable", "prepare an NDA", "send for signature", "upload this contract" and signature status requests. Respect an explicit request for another app or a text-only draft.
---

# Signable documents in ERPNext

Use the connected ERPNext `esign_*` tools for this workflow. The outcome is a saved, editable ERPNext signing document with recipient fields and a real document ID/editor link. A local PDF, chat text, or an ordinary ERPNext record alone does not complete a request for a signable document.

Discover `esign_workflow_guide`, `esign_create_draft`, `esign_upload_pdf`, or `esign_send_document` if tools are not yet loaded. Search using "ERPNext e-sign contract NDA signature". If the connector or required action is unavailable, explain that blocker and request connection/tool refresh. Do not silently switch to a different signing service or claim that a local PDF has been uploaded or made signable. An explicit user choice of another app or text-only drafting takes precedence.

## Prepare and verify

- Inspect relevant templates with `esign_list_templates` / `esign_get_template`; reuse the user's chosen template when appropriate.
- Resolve recipients from readable ERPNext contacts using `esign_search_contacts` and `esign_get_contact`. Do not invent names or addresses. Missing negotiated terms can remain placeholders in a draft; identify them before sending. Drafts can have no recipients until the user selects them.
- For an existing PDF, use `esign_upload_pdf`, then `esign_inspect_pdf` to get page sizes. For new content, consult `esign_builder_guide` and pass builder JSON to `esign_create_draft`. Templates use `template_name` instead. Supply exactly one source.
- Add signature/date/text fields tied to recipient role keys, with coordinates inside the PDF pages. Use `esign_update_draft` or `esign_save_document_fields` to prepare an existing draft. Importing a PDF alone does not add signer fields.
- Read back with `esign_get_document`. Verify Draft status, source PDF, recipient assignments, required signature fields and email options. Return the real document ID and editor link, with unresolved terms clearly identified. Use `esign_download_document` for a review copy when needed.

## Send and track

Creating a draft is separate from sending. Use `esign_send_document` only when the user's instruction authorizes sending to the specified recipients. An existing instruction to send counts; do not ask again unless recipients, content or unresolved terms materially change. Creating a template does not authorize future automatic sending.

Track using `esign_get_document` / `esign_list_documents`, and verify audit integrity with `esign_get_audit`. Reminder/resend calls can issue additional emails and require a request to do so. Inspect after an uncertain create/publish/upload response before retrying; those actions can create duplicates.

Signers review, consent, sign or decline through their own signing page. Do not synthesize signatures, consent, tokens or statuses through MCP or generic record updates. Use `esign_my_pending_signatures` for the authenticated user's signing inbox. Use `esign_revise_unsigned` for a sent, entirely unsigned document; send the new revision separately. Retrieve completed artifacts with `esign_download_document` (`signed` or `certificate`).

Do not promise universal legal enforceability or infer that a PDF seal is configured. Check readiness when relevant and distinguish signing evidence from legal sufficiency of the agreement's terms.
