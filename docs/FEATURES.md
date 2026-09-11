# Upstream feature comparison

Compared against upstream commit `d33746b`, its README, compiled application routes, and server APIs. The first local-review UI omitted some controls; this follow-up restores them. Backend security checks remain in place.

| Original capability | Where it lives now |
| --- | --- |
| PDF upload and reusable templates | Prepare a document; Templates |
| Signature, Initial, Name, Email, Date Signed, Text, Checkbox, Dropdown | Complete field toolbar; Label and Stamp also exposed |
| Repeat across pages | Select a field → Repeat on all pages; duplicate and coordinate/size controls |
| Multiple recipients, sequential/parallel routing | Preparation recipient list and signing order |
| Guest signing links | Public signing screen |
| Draw, type, upload signature | Three signature-entry options; PNG/JPG upload |
| Signed PDF, certificate, audit trail | Document detail and completed signing screen |
| Invitations, reminders, expiration | Existing backend delivery/scheduler; manual reminder and explicit expiry controls |
| Template lifecycle and versions | Edit/duplicate/archive; save and publish uses existing version snapshots |
| Automatic ERP events and value/date triggers | Template rules & ERP automation; existing server trigger handlers |
| ERP prefill and recipient mappings | Field inspector and template automation settings |
| Editable email templates | Settings → Email templates → native Frappe Desk editor |
| Organization policies and email account setup | Settings → Organizations / Manage email → native Frappe editors |
| Application configuration | Settings → Application settings → native Frappe editor |
| Dark mode | Appearance control in workspace and signer header; stored in this browser |
| My signing inbox | Awaiting my signature |
| Dashboard totals and throughput | Document summary and expandable Activity overview; recent documents remain the main register |

Some administrative forms intentionally open Frappe Desk instead of duplicating Frappe's existing editors. These require a real Frappe site and the relevant role; the fictional local preview does not emulate Desk.

## Deliberate protections, not missing product features

Unimplemented authentication modes are not presented as working identity verification. Uploaded PDFs must be within the documented limits and have existing form widgets flattened. Signing requires consent; sent evidence cannot be edited through generic Desk writes. These protections remain even when restoring UI parity.

This comparison is not a claim of pixel-for-pixel parity or exhaustive automated testing of every upstream edge case. Production ERPNext, email delivery, scheduler and queue validation still await staging after local design review.
