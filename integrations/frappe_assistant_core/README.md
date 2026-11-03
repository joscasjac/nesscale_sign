# ERPNext MCP integration

Open E-Sign registers 61 actions with Frappe Assistant Core's native `assistant_tools` hook. No separate server or connector fork is required. All operations run as the connected ERPNext user and call the application's existing services. Existing role and document permissions remain in effect.

## Deployment and activation

1. Deploy this app revision to the existing bench and migrate normally. It requires Python 3.14 and the dependencies in `pyproject.toml`.
2. Restart workers, refresh FAC tool discovery, and keep the existing **Custom Tools** plugin enabled. Enable the `esign_*` tools for the intended connector roles in FAC settings. Do not grant broader ERPNext roles just to expose tools.
3. Refresh/reconnect the ERPNext client to reload its cached MCP tool list.
4. Smoke-test `esign_builder_guide`, `esign_list_documents`, and a private test PDF upload/draft/download. Do not send an invitation without explicit instruction.

The previous `fac_plugins` discovery patch has been removed. This revision does not register that hook; do not enable a second Open E-Sign plugin alongside native custom tools.

## Workflow

- Discover recipients with `esign_search_contacts` / `esign_get_contact`.
- Create from builder content, a template, or a PDF uploaded using `esign_upload_pdf`.
- Place recipient fields, choose email templates/attachments and routing in `esign_create_draft` or `esign_update_draft`.
- Inspect the draft, its editor URL and source PDF. Creation never sends.
- Send on user instruction using `esign_send_document`. An already-sent document returns `already_sent` without duplicate invitations.
- Track status and audit integrity; remind/resend, void or revise unsigned documents when requested.
- Retrieve the signed PDF and completion certificate with `esign_download_document`.

Signers personally review, consent, sign or decline in the existing signing page. MCP does not impersonate signers, manufacture consent, expose bearer signing tokens or directly set lifecycle statuses. `esign_my_pending_signatures` hands the authenticated user back to their app inbox. Cryptographic seals and audit records continue to use the existing app configuration; adding MCP tools does not itself confer a legal certification.

## File transfer

`esign_upload_pdf` accepts `{file_name, content_base64}` (raw base64, not a data URL), limited to 15 MiB, 100 pages, no encryption or existing form widgets. It returns a private file URL, File record ID, SHA256 and page dimensions. `esign_upload_image` supports PNG/JPEG assets up to 5 MiB/16 million pixels. Pass the File record ID in the JSON array used by `data.email_attachments`.

For downloads, first request metadata (the default). Set `include_content: true` for base64 chunks, up to 262144 decoded bytes per call; continue from `next_offset` until `eof`. Decode each chunk separately and concatenate the bytes. Compare the final SHA256 to the returned hash. If the hash changes during transfer, restart from offset zero. Private URLs require normal ERPNext authentication; they are not public links. Large uploads should be transferred programmatically by the MCP client, not copied into a conversation; client request-size limits may be lower than the server limit.

## Safety and retries

Schemas reject unknown keys, including signer tokens, status and completion metadata. Manager settings still require manager roles. File reads check either the File's read permission or the owning envelope's read permission. Uploads require document and File create permission. Mutating adapter calls use a database savepoint and rollback on failure. The adapter suppresses document bodies, file bytes and nested credentials in its execution logs.

Creation, upload, duplicate, publish, resend and reminder calls are not promised idempotent. After an uncertain response, inspect existing records before retrying. Reminder/resend tools may send a new message on every successful call. Automatic template sending and account configuration are explicitly marked as external-side-effect operations.

## Validation

Fast isolated adapter tests: `.venv/bin/python -m pytest tests_unit`.
Full Frappe regression tests on an isolated test site: `bench --site TEST_SITE run-tests --app nesscale_sign`.
Never enable or run this integration suite on a production site. Live activation is a separate deployment step; passing source tests does not mean the client has refreshed its tool list.

## Tool inventory

The authoritative schemas and action allowlist are in `nesscale_sign/mcp/catalog.py` and `nesscale_sign/mcp/tools.py`. Explicit class modules support FAC discovery; hook/registry parity is tested.

| Area | Tools |
| --- | --- |
| Documents | builder guide; list/get/create/update; save fields; send; resend; remind; void; delete draft; revise unsigned; retry completion; audit; my pending signatures |
| Files | upload PDF/image; inspect PDF; download file/document; render PDF; combine PDFs |
| Templates | list/get/create/update; replace PDF; save fields/roles; publish; archive; duplicate |
| Contacts | search, read, create |
| Reporting | totals, recent activity, daily throughput |
| Organizations/settings | list/save organizations, read/update settings, readiness |
| Email | list providers/accounts/senders; create/update/delete account; list/read/save/preview/restore email templates; create invitation template; validate attachments |
| Automation | discover DocTypes, fields and trigger events; configure through template options |

## AI discovery

The app publishes the `erpnext-signable-documents` FAC skill through `assistant_skills`, linked to `esign_workflow_guide`. FAC exposes it as an MCP resource, and the read-only guide exposes the same instructions as a tool for clients that do not consume resources. The guide, upload, create and send tool descriptions use ordinary task language and point to the guide. These descriptions travel with the MCP server to Claude, Codex and other compatible clients; users do not need to install a local skill to access them.

An optional client-level preference can improve routing when the client does not automatically read MCP resources or choose the guide tool:

> For signable documents, contracts, NDAs and signature requests, use our connected ERPNext Nesscale Sign/Open E-Sign MCP workflow by default. Discover `esign_workflow_guide` first. Create and verify the ERPNext draft and return its real link. If these tools are unavailable, report the connector/tool-discovery blocker instead of silently using another signing service or returning only a local file. Respect an explicit request for a different app or a text-only draft. Send invitations only when my instruction authorizes sending to those recipients.

Acceptance cases after refreshing the client: "Make this PDF signable" should use upload, draft creation and field placement; "Prepare an NDA" should create a draft or identify missing terms; "Send this contract to [recipient] for signature" should inspect and send the selected ERPNext document. "Draft wording only" should remain text-only. A disconnected client should report missing tools. These are behavioral smoke tests, not a guarantee that every model will follow routing instructions.
