# ERPNext connector integration

Open E-Sign provides nine Frappe Assistant Core tools through an optional installed-app plugin. The e-sign app remains usable without the connector. No deployment or email is performed when these files are installed.

## Deployment

The connector reference is `buildswithpaul/Frappe_Assistant_Core` v2.5.1 (`7ddc433`). That version only discovers its own plugin directory. This package includes a small connector patch to also discover installed-app plugins declared by `fac_plugins` in Frappe hooks. Core plugins and existing role/tool enablement remain in place; duplicate plugin names cannot override a core plugin.

1. Apply `app-plugin-discovery.patch` to the connector source checkout (check first with `git apply --check PATH_TO_PATCH`, then `git apply PATH_TO_PATCH`). Include that change in the connector revision you deploy. Do not patch a transient running container.
2. Deploy the updated connector and this e-sign app to the same Frappe site. Install the app's dependencies and migrate the site normally.
3. Restart the web workers so plugin discovery reads the new hook. Refresh plugin discovery in Frappe Assistant Core and enable **Open E-Sign**. Keep the connector user's required NS Envelope/NS Template and Contact access permissions; the tools use that user's session and do not elevate document permissions.
4. Refresh/reconnect the ERPNext connector in the client to reload its tool list. Verify that `esign_builder_guide` appears. Existing connector clients may cache the previous list.
5. Create one draft and open its `editor_url` before authorizing a signing invitation.

Both source updates are required with this connector version. Deploying only the e-sign app will not make its tools discoverable by an unpatched connector. For another connector revision, check the patch rather than force-applying it.

## Tools

| Tool | Action |
| --- | --- |
| `esign_builder_guide` | Read the content format, limits and example payload |
| `esign_list_templates` | List readable templates |
| `esign_get_template` | Read roles, fields and PDF metrics |
| `esign_list_documents` | Find documents and their statuses |
| `esign_get_document` | Read a document, fields, audit and editor URL |
| `esign_create_draft` | Render builder content, use a private PDF, or instantiate a template; never sends |
| `esign_update_draft` | Edit a draft, regenerate content and replace field placement |
| `esign_send_document` | Send on explicit user instruction; repeated calls for a sent document do not resend |
| `esign_revise_unsigned` | Withdraw unsigned links and create a new draft requiring a separate send |

Use existing ERPNext Contact lookup tools for recipient data. Use the existing PDF upload UI for private file uploads; then pass that private URL to the create-draft tool. File uploads are not added to this tool set.

Creation is not idempotent: after an uncertain response, search for the draft before retrying. Mutating adapter calls use a database savepoint, so a validation failure does not leave a partially created envelope when the connector handles the exception. Existing permission checks, signing restrictions, private-file checks and audit events are preserved. Signing access tokens are excluded from envelope responses.

The build format currently requires explicit page/block geometry; the guide explains the dimensions. It is not an automatic natural-language pagination service. Generated content remains editable in the web builder, and overflow fails visibly instead of clipping silently.

## Local verification

- 64 e-sign regression tests passed, including new create/update/template/send-retry/permission tests.
- Two connector discovery tests passed.
- The actual FAC PluginDiscovery and tool loader found all nine tools using the installed app hook, and the real adapter executed the guide successfully.
- Live connector activation and invitation delivery still need a deployment smoke test; no production deployment was performed.
