const demoContacts=[{name:"demo-alex",full_name:"Alex Morgan",email_id:"alex@example.test"},{name:"demo-sam",full_name:"Sam Rivera",email_id:"sam@example.test"}];
// A deliberately separate, loopback-only preview service. Never built or shipped to Frappe.
import { readFile } from "node:fs/promises";
import express from "express";
import {renderBuilder} from "./builder-preview.mjs";
import { PDFDocument, StandardFonts, rgb } from "pdf-lib";
import { spawn } from "node:child_process";
import { fileURLToPath } from "node:url";
const app = express();
app.use(express.json({ limit: "12mb" }));
const timestamp = () => new Date().toISOString();
let serial = 108;
const storage = new Map();
const documents = new Map();
const templates = new Map();
const emailTemplates=new Map(), attachmentFiles=new Map();
async function samplePDF() {
  const pdf = await PDFDocument.create(),
    font = await pdf.embedFont(StandardFonts.Helvetica),
    serif = await pdf.embedFont(StandardFonts.TimesRoman);
  const page = pdf.addPage([595, 842]);
  const ink = rgb(0.16, 0.21, 0.17),
    muted = rgb(0.39, 0.44, 0.39);
  page.drawText("NORTHLINE STUDIO", {
    x: 55,
    y: 780,
    size: 10,
    font,
    color: muted,
  });
  page.drawText("Service agreement", {
    x: 55,
    y: 718,
    size: 29,
    font: serif,
    color: ink,
  });
  page.drawText("A clear understanding. A good beginning.", {
    x: 55,
    y: 689,
    size: 11,
    font,
    color: muted,
  });
  page.drawLine({
    start: { x: 55, y: 664 },
    end: { x: 540, y: 664 },
    thickness: 0.5,
    color: rgb(0.8, 0.83, 0.79),
  });
  const lines = [
    [
      "The parties",
      "This agreement is between Northline Studio and Meridian Works.",
    ],
    [
      "Scope of work",
      "Design and production services as described in the approved proposal.",
    ],
    [
      "Schedule",
      "Work begins on the agreed start date after both parties have signed.",
    ],
    [
      "Payment",
      "Invoices follow the milestones set out in the attached statement of work.",
    ],
    [
      "Agreement",
      "By signing below, each party agrees to the terms of this document.",
    ],
  ];
  let y = 627;
  for (const [title, body] of lines) {
    page.drawText(title, { x: 55, y, size: 13, font: serif, color: ink });
    page.drawText(body, { x: 55, y: y - 24, size: 10, font, color: muted });
    y -= 77;
  }
  page.drawText("Name", { x: 60, y: 196, size: 9, font, color: muted });
  page.drawText("Signature", { x: 60, y: 135, size: 9, font, color: muted });
  page.drawLine({
    start: { x: 55, y: 70 },
    end: { x: 540, y: 70 },
    thickness: 0.5,
    color: rgb(0.8, 0.83, 0.79),
  });
  page.drawText("FICTIONAL PREVIEW DOCUMENT  |  Not a real contract", {
    x: 55,
    y: 50,
    size: 8,
    font,
    color: muted,
  });
  page.drawText("1 / 1", { x: 512, y: 50, size: 8, font, color: muted });
  return Buffer.from(await pdf.save());
}
const base = await samplePDF();
storage.set("/demo/document.pdf", base);
const baseFields = [
  {
    field_key: "full-name",
    field_type: "Name",
    label: "Full name",
    page: 1,
    pos_x: 0.1,
    pos_y: 0.78,
    width: 0.45,
    height: 0.04,
    required: 1,
    signer_role: "signer-1",
    signer_email: "alex@example.com",
    editable: true,
  },
  {
    field_key: "signature",
    field_type: "Signature",
    label: "Signature",
    page: 1,
    pos_x: 0.1,
    pos_y: 0.85,
    width: 0.45,
    height: 0.055,
    required: 1,
    signer_role: "signer-1",
    signer_email: "alex@example.com",
    editable: true,
  },
];
baseFields.push({ ...baseFields[0], field_key: "agreement-date", field_type: "Date", label: "Agreement date", pos_x: 0.64, width: 0.26 });
const titles = [
  "Service agreement — Meridian Works",
  "Photography release — Autumn campaign",
  "Consulting agreement — Westwood",
  "Supplier agreement — Field & Form",
  "Non-disclosure agreement — Juniper",
  "Project handover — Atelier No. 4",
  "Employment offer — Design lead",
];
const statuses = [
  "Sent",
  "Draft",
  "Completed",
  "In Progress",
  "Completed",
  "Sent",
  "Draft",
];
for (let i = 0; i < titles.length; i++) {
  const name = `NS-ENV-2026-${String(101 + i).padStart(5, "0")}`;
  documents.set(name, {
    envelope: {
      name,
      title: titles[i],
      status: statuses[i],
      sender_name: "Jordan Ellis",
      routing_type: "Sequential",
      modified: `2026-09-${String(11 - Math.floor(i / 2)).padStart(2, "0")}T10:30:00`,
      source_pdf: "/demo/document.pdf",
      page_count: 1,
      signers: [
        {
          name: "signer-" + i,
          signer_name: "Alex Morgan",
          signer_email: "alex@example.com",
          role_key: "signer-1",
          status: statuses[i] === "Completed" ? "Signed" : "Sent",
          signing_order: 1,
        },
      ],
      seal_status: "Not configured",
      source_sha256: "recorded-in-preview",
      finalization_status: statuses[i] === "Completed" ? "Complete" : null,
    },
    fields: structuredClone(baseFields),
    audit: [
      {
        name: "created-" + i,
        action: "Created",
        timestamp: "2026-09-09T10:00:00",
        signer_name: "Jordan Ellis",
      },
      {
        name: "sent-" + i,
        action: "Sent",
        timestamp: "2026-09-10T11:00:00",
        signer_name: "Jordan Ellis",
      },
    ],
  });
}
templates.set("NS-TMPL-001", {
  template: {
    name: "NS-TMPL-001",
    title: "Service agreement",
    status: "Active",
    page_count: 1,
    pdf_file: "/demo/document.pdf",
    routing_type: "Sequential",
    modified: timestamp(),
    signer_roles: [
      { role_key: "signer-1", role_label: "Client", signing_order: 1 },
    ],
  },
  fields: structuredClone(baseFields),
});
let signId = "NS-ENV-2026-00101";
app.get("/demo/config", (_, res) => res.json({ demo: true }));
app.get("/demo/:file", (req, res) => {
  const file = storage.get("/demo/" + req.params.file);
  file ? res.type("pdf").send(file) : res.sendStatus(404);
});
app.post(
  "/api/method/upload_file",
  express.raw({ type: () => true, limit: "16mb" }),
  (req, res) => {
    try {
      const boundary = req.headers["content-type"].split("boundary=")[1];
      const b = Buffer.from(req.body);
      const begin = b.indexOf(Buffer.from("\r\n\r\n")) + 4;
      const end = b.indexOf(Buffer.from("\r\n--" + boundary), begin);
      const content = b.subarray(begin, end);

      const url = "/demo/upload-" + serial++ + ".pdf";
      storage.set(url, content);
      const name="file-"+serial++;attachmentFiles.set(name,{name,file_name:"Uploaded attachment",file_url:url});
      res.json({ message: { file_url: url, name } });
    } catch {
      res.status(400).json({ message: "Choose a valid PDF under 15 MB." });
    }
  },
);
app.all("/api/method/nesscale_sign.api.:module.:method", async (req, res) => {
  try {
    const args = { ...req.query, ...req.body },
      key = req.params.module + "." + req.params.method;
    let result;
    const doc = documents.get(args.name);
    const tmpl = templates.get(args.name);
    const list = (map, field) =>
      [...map.values()]
        .map((d) => d[field])
        .filter(
          (d) =>
            (!args.status || d.status === args.status) &&
            (!args.search ||
              d.title.toLowerCase().includes(args.search.toLowerCase())),
        )
        .slice(
          Number(args.start || 0),
          Number(args.start || 0) + Number(args.page_length || 20),
        );
    switch (key) {
      case "builder.combine_pdfs": {const doc=await PDFDocument.create();for(const url of args.urls){const source=await PDFDocument.load(storage.get(url)||base);for(const p of await doc.copyPages(source,source.getPageIndices()))doc.addPage(p);}const url='/demo/combined-'+serial+++'.pdf';storage.set(url,Buffer.from(await doc.save()));result={file_url:url,page_count:doc.getPageCount()};break;}
      case "builder.render": {let pdf=await renderBuilder(args.data);if(args.source_pdf){const source=await PDFDocument.load(storage.get(args.source_pdf)||base);const overlays=await source.embedPdf(pdf);overlays.forEach((p,i)=>{if(args.data.pages[i]?.blocks.length){const sheet=source.getPage(i);sheet.drawPage(p,{x:0,y:0,width:sheet.getWidth(),height:sheet.getHeight()});}});pdf=Buffer.from(await source.save());}const url="/demo/built-"+serial+++".pdf";storage.set(url,pdf);result={file_url:url};break;}
      case "mail.list_senders": result=[{name:"Demo sender",email_id:"documents@example.test"}];break;
      case "mail.list_templates": result=[...emailTemplates.values()];break;
      case "mail.create_template": result={name:args.name,subject:args.subject,body:args.body};emailTemplates.set(args.name,result);break;
      case "mail.list_attachments": result=JSON.parse(args.names||"[]").map(id=>attachmentFiles.get(id)).filter(Boolean);break;
      case "contacts.create_contact": {result={name:'demo-contact-'+serial++,full_name:args.full_name,email_id:args.email_id};demoContacts.push(result);break;}
      case "contacts.search_contacts":
        result = demoContacts.filter(c => c.full_name.toLowerCase().includes(String(args.query || "").toLowerCase())); break;
      case "contacts.get_contact_prefill":
        result=demoContacts.find(c=>c.name===args.name);if(!result)throw Error("Contact not found"); break;
      case "dashboard.get_stats": {
        const counts = {};
        for (const { envelope: d } of documents.values())
          counts[d.status] = (counts[d.status] || 0) + 1;
        result = {
          counts,
          total: documents.size,
          completion_rate: Math.round((counts.Completed || 0) / documents.size * 100),
          templates: templates.size,
          awaiting_me: 1,
          completed: counts.Completed || 0,
          in_flight: (counts.Sent || 0) + (counts["In Progress"] || 0),
        };
        break;
      }
      case "dashboard.throughput":
        result = [{day: '2026-09-09', count: 1}, {day: '2026-09-10', count: 1}]; break;
      case "envelope.my_pending_signatures":
        result = [...documents.values()].filter(d => ['Sent', 'In Progress'].includes(d.envelope.status)).map(d => ({ ...d.envelope, token: 'demo-signer' })).slice(0,1);
        break;
      case "envelope.list_envelopes":
        result = list(documents, "envelope");
        break;
      case "template.list_templates":
        result = list(templates, "template");
        break;
      case "envelope.revise_unsigned": {const original=documents.get(args.name);if(!original||!['Sent','In Progress'].includes(original.envelope.status)||original.envelope.signers.some(s=>s.status==='Signed'))throw Error('This document cannot be revised');const copy=structuredClone(original);copy.envelope.name='NS-ENV-2026-'+String(serial++).padStart(5,'0');copy.envelope.status='Draft';copy.envelope.signers.forEach(s=>{s.status='Pending';s.token=null;});original.envelope.status='Voided';documents.set(copy.envelope.name,copy);result={name:copy.envelope.name};break;}
      case "envelope.get_envelope":
        if (!doc) throw Error("Document not found.");
        result = doc;
        break;
      case "template.get_template":
        if (!tmpl) throw Error("Template not found.");
        result = tmpl;
        break;
      case "envelope.preview_pdf":
      case "envelope.download_signed":
      case "envelope.download_certificate":
      case "template.preview_pdf": {
        const url =
          tmpl?.template.pdf_file ||
          doc?.envelope.signed_pdf ||
          doc?.envelope.source_pdf;
        res.type("pdf").send(storage.get(url) || base);
        return;
      }
      case "settings.get_readiness":
        result = { email_configured: true, seal_configured: false };
        break;
      case "envelope.create_adhoc":
      case "envelope.create_from_template": {
        const data = args.data;
        const t = templates.get(args.template);
        const name = `NS-ENV-2026-${String(serial++).padStart(5, "0")}`;
        const content =
          storage.get(data.pdf_file || t?.template.pdf_file) || base;
        const p = await PDFDocument.load(content);
        const d = {
          envelope: {
            ...data,
            name,
            status: "Draft",
            source_pdf: data.pdf_file || t?.template.pdf_file,
            sender_name: "Jordan Ellis",
            modified: timestamp(),
            page_count: p.getPageCount(),
            signers: data.signers.map((s, i) => ({
              ...s,
              name: "recipient-" + i,
              status: "Pending",
            })),
          },
          fields: data.fields || structuredClone(t.fields),
          audit: [
            {
              name: crypto.randomUUID(),
              action: "Created",
              timestamp: timestamp(),
            },
          ],
        };
        documents.set(name, d);
        result = d.envelope;
        break;
      }
      case "envelope.update_envelope":
        Object.assign(doc.envelope, args.data);
        result = doc.envelope;
        break;
      case "envelope.save_envelope_fields":
        doc.fields = args.fields.map((f) => ({
          ...f,
          signer_email: doc.envelope.signers.find(
            (s) => s.role_key === f.signer_role,
          )?.signer_email,
          editable: true,
        }));
        result = { saved: true };
        break;
      case "envelope.send_envelope":
        if (
          !doc.envelope.signers.every(
            (s) => s.signer_name && s.signer_email.includes("@"),
          )
        )
          throw Error("Add a name and valid email for every recipient.");
        doc.envelope.status = "Sent";
        doc.envelope.signers.forEach((s) => (s.status = "Sent"));
        doc.audit.push({
          name: crypto.randomUUID(),
          action: "Sent",
          timestamp: timestamp(),
        });
        signId = doc.envelope.name;
        result = doc.envelope;
        break;
      case "envelope.remind_envelope":
        doc.audit.push({
          name: crypto.randomUUID(),
          action: "Reminded",
          timestamp: timestamp(),
        });
        result = { reminded: 1 };
        break;
      case "envelope.void_envelope":
        doc.envelope.status = "Voided";
        result = doc.envelope;
        break;
      case "template.create_template": {
        const name = "NS-TMPL-" + serial++;
        const t = {
          template: {
            ...args.data,
            name,
            status: "Draft",
            modified: timestamp(),
            page_count: 1,
          },
          fields: [],
        };
        templates.set(name, t);
        result = t.template;
        break;
      }
      case "template.save_template_fields":
        tmpl.fields = args.fields;
        result = { saved: args.fields.length };
        break;
      case "template.update_template":
        Object.assign(tmpl.template, args.data); result = tmpl.template; break;
      case "template.set_template_pdf":
        tmpl.template.pdf_file = args.file_url; result = tmpl.template; break;
      case "template.save_template_roles":
        tmpl.template.signer_roles = args.roles; result = tmpl.template; break;
      case "template.archive_template":
        tmpl.template.status = 'Archived'; result = tmpl.template; break;
      case "template.duplicate_template": {
        const name = "NS-TMPL-" + serial++;
        const copy = structuredClone(tmpl);
        copy.template.name = name;
        copy.template.title += ' (copy)';
        copy.template.status = 'Draft';
        templates.set(name, copy); result = copy.template; break;
      }
      case "template.publish_template":
        tmpl.template.status = "Active";
        result = tmpl.template;
        break;
      case "signing.get_context": {
        const d = documents.get(signId);
        const signer = d.envelope.signers[0];
        if (["Voided", "Declined"].includes(d.envelope.status))
          throw Error("This document is no longer available.");
        result = {
          envelope: d.envelope,
          signer: {
            name: signer.signer_name,
            email: signer.signer_email,
            status: signer.status,
            can_sign: signer.status !== "Signed",
          },
          fields: d.fields.map((f) => ({ ...f, editable: true })),
          pdf_url: d.envelope.source_pdf,
          consent_text:
            "I have reviewed this document and agree to sign it electronically.",
          consent_version: "2026-09-11",
        };
        break;
      }
      case "signing.save_progress":
        result = { saved: true };
        break;
      case "signing.submit": {
        if (args.consent !== true)
          throw Error("Please agree to sign electronically.");
        const d = documents.get(signId);
        const pdf = await PDFDocument.load(
          storage.get(d.envelope.source_pdf) || base,
        );
        const font = await pdf.embedFont(StandardFonts.Helvetica);
        for (const f of d.fields) {
          const p = pdf.getPage((f.page || 1) - 1),
            { width: w, height: h } = p.getSize();
          if (
            ["Signature", "Initial", "Stamp"].includes(f.field_type) &&
            args.signature?.image
          ) {
            const img = await pdf.embedPng(args.signature.image);
            p.drawImage(img, {
              x: f.pos_x * w,
              y: h - (f.pos_y + f.height) * h,
              width: f.width * w,
              height: f.height * h,
            });
          } else if (args.values?.[f.field_key])
            p.drawText(String(args.values[f.field_key]), {
              x: f.pos_x * w,
              y: h - (f.pos_y + f.height) * h,
              size: 12,
              font,
            });
        }
        const certificate = await PDFDocument.load(await readFile(new URL('../../docs/examples/completion-certificate.pdf', import.meta.url)));
        for (const page of await pdf.copyPages(certificate, certificate.getPageIndices())) pdf.addPage(page);
        const url = "/demo/completed-" + serial++ + ".pdf";
        storage.set(url, Buffer.from(await pdf.save()));
        d.envelope.signed_pdf = url;
        d.envelope.status = "Completed";
        d.envelope.finalization_status = "Complete";
        d.envelope.signers[0].status = "Signed";
        d.audit.push({
          name: crypto.randomUUID(),
          action: "Completed",
          timestamp: timestamp(),
        });
        result = { status: "completed" };
        break;
      }
      case "signing.decline":
        documents.get(signId).envelope.status = "Declined";
        result = { status: "declined" };
        break;
      case "signing.download_certificate": {
        if (documents.get(signId).envelope.status !== 'Completed') throw Error('The completion certificate is not available.');
        const certificate = await readFile(new URL('../../docs/examples/completion-certificate.pdf', import.meta.url));
        res.type('pdf').set('Content-Disposition', 'attachment; filename="fictional-completion-certificate.pdf"').send(certificate);
        return;
      }
      case "signing.download_completed": {
        const d = documents.get(signId);
        res
          .type("pdf")
          .set(
            "Content-Disposition",
            'attachment; filename="preview-signed.pdf"',
          )
          .send(storage.get(d.envelope.signed_pdf) || base);
        return;
      }
      default:
        res
          .status(404)
          .json({
            message: "This action is not available in the local preview.",
          });
        return;
    }
    res.json({ message: result });
  } catch (e) {
    res.status(400).json({ message: e.message });
  }
});
app.listen(4174, "127.0.0.1", () =>
  console.log("Preview API: http://127.0.0.1:4174 (fictional data only)"),
);
const vite = spawn(
  process.execPath,
  [
    "node_modules/vite/bin/vite.js",
    "--host",
    "127.0.0.1",
    "--port",
    "4173",
    "--strictPort",
  ],
  {
    cwd: fileURLToPath(new URL("..", import.meta.url)),
    stdio: "inherit",
    env: { ...process.env, LOCAL_PREVIEW: "1" },
  },
);
for (const signal of ["SIGINT", "SIGTERM"])
  process.on(signal, () => {
    vite.kill(signal);
    process.exit();
  });
vite.on("exit", () => process.exit());
