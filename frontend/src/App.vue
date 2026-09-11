<script setup>
import { ref, onMounted, computed, onBeforeUnmount } from "vue";
import {
	FileText,
	Files,
	ArrowUpRight,
	Plus,
	Search,
	ArrowLeft,
	Check,
	ChevronLeft,
	ChevronRight,
	Download,
	Send,
	Settings,
	PenLine,
	ExternalLink,
	Trash2,
	RefreshCw,
	Menu,
} from "@lucide/vue";
import { api, date, downloadUrl, upload } from "./api";
import PdfPage from "./components/PdfPage.vue";
import ActivitySummary from "./components/ActivitySummary.vue";
import TemplateOptions from "./components/TemplateOptions.vue";
import BrandLogo from "./components/BrandLogo.vue";
import { fieldTypes, repeatField } from "./fields";
import SignaturePad from "./components/SignaturePad.vue";
const theme = ref("light");
function setTheme(value) {
	theme.value = value;
	document.documentElement.dataset.theme = value;
	try {
		localStorage.setItem("open-esign-theme", value);
	} catch {}
}
try {
	setTheme(localStorage.getItem("open-esign-theme") || "light");
} catch {}
function repeatSelected() {
	run(async () => {
		fields.value.push(...repeatField(selected.value, pages.value, fields.value));
		flash("Field repeated across all pages.");
	});
}
const userInitial = (window.user?.[0] || "W").toUpperCase();
const root = "/nesscale-sign";
const route = ref(location.pathname),
	mobile = ref(false),
	rows = ref([]),
	templates = ref([]),
	filter = ref("All documents"),
	query = ref(""),
	offset = ref(0),
	loading = ref(false),
	busy = ref(false),
	error = ref(""),
	notice = ref(""),
	detail = ref(null),
	page = ref(1),
	pages = ref(1),
	stats = ref({ counts: {} }),
	settings = ref(null);
const demo = ref(false),
	signContext = ref(null),
	values = ref({}),
	signature = ref(null),
	consent = ref(false),
	declining = ref(false),
	reason = ref(""),
	selected = ref(null),
	fields = ref([]),
	pdfUrl = ref(""),
	draftId = ref(null);
const form = ref({
	title: "",
	signers: [{ signer_name: "", signer_email: "", role_key: "signer-1", signing_order: 1 }],
	routing_type: "Sequential",
	message: "",
	source_doctype: "",
	source_name: "",
});
let poll;
const isSigner = computed(() => route.value.startsWith("/sign/"));
const token = computed(() => decodeURIComponent(route.value.split("/")[2] || ""));
const view = computed(() => (isSigner.value ? "sign" : route.value.split("/")[2] || "documents"));
const isPending = computed(() => view.value === "my-sign");
const isTemplate = computed(() => view.value === "templates");
const filteredStatus = computed(
	() =>
		({
			"Waiting for others": "Sent",
			Completed: "Completed",
			Drafts: "Draft",
			"In progress": "In Progress",
			Declined: "Declined",
			Expired: "Expired",
			Voided: "Voided",
		})[filter.value],
);
const ownFields = computed(() =>
	(signContext.value?.fields || []).filter(
		(f) => f.editable && !["Label", "Date Signed"].includes(f.field_type),
	),
);
const requiredRemaining = computed(
	() =>
		ownFields.value.filter(
			(f) =>
				f.required &&
				(["Signature", "Initial", "Stamp"].includes(f.field_type)
					? !signature.value
					: !values.value[f.field_key]),
		).length,
);
function goHome() {
	if (isSigner.value && window.user === "Guest" && !demo.value) location.assign(root);
	else go(root);
}
function go(path) {
	if (path === root || path === root + "/templates") {
		filter.value = "All documents";
		query.value = "";
		offset.value = 0;
	}
	history.pushState({}, "", path);
	route.value = path;
	mobile.value = false;
	return load();
}
function escapeMenu(e) {
	if (e.key === "Escape") mobile.value = false;
}
function pop() {
	route.value = location.pathname;
	load();
}
function flash(text) {
	notice.value = text;
}
async function run(fn) {
	busy.value = true;
	error.value = "";
	try {
		return await fn();
	} catch (e) {
		error.value = e.message;
	} finally {
		busy.value = false;
	}
}
async function load() {
	clearTimeout(poll);
	error.value = "";
	notice.value = "";
	loading.value = true;
	detail.value = null;
	signContext.value = null;
	page.value = 1;
	try {
		if (isSigner.value) {
			signContext.value = await api("signing.get_context", { token: token.value });
			values.value = Object.fromEntries(
				signContext.value.fields.map((f) => [f.field_key, f.value || ""]),
			);
			if (signContext.value.envelope.finalization_status === "Pending")
				poll = setTimeout(load, 3000);
		} else if (view.value === "document") {
			detail.value = await api("envelope.get_envelope", {
				name: decodeURIComponent(route.value.split("/")[3]),
			});
			pdfUrl.value = downloadUrl("envelope.preview_pdf", {
				name: detail.value.envelope.name,
			});
			if (detail.value.envelope.finalization_status === "Pending")
				poll = setTimeout(load, 3000);
		} else if (view.value === "new") {
			draftId.value = null;
			editingTemplate.value = null;
			fields.value = [];
			pdfUrl.value = "";
			form.value = {
				title: "",
				signers: [
					{ signer_name: "", signer_email: "", role_key: "signer-1", signing_order: 1 },
				],
				routing_type: "Sequential",
				message: "",
			};
			templates.value = await api("template.list_templates", {
				status: "Active",
				page_length: 100,
			});
		} else if (isPending.value) rows.value = await api("envelope.my_pending_signatures");
		else if (view.value === "settings") settings.value = await api("settings.get_readiness");
		else {
			rows.value = await api(
				isTemplate.value ? "template.list_templates" : "envelope.list_envelopes",
				{
					status: filteredStatus.value,
					search: query.value,
					start: offset.value,
					page_length: 20,
				},
			);
			stats.value = await api("dashboard.get_stats");
		}
	} catch (e) {
		error.value = e.message;
	} finally {
		loading.value = false;
	}
}
async function search() {
	offset.value = 0;
	await load();
}
async function setFilter(f) {
	filter.value = f;
	await search();
}
function statusClass(status) {
	return (
		{
			Completed: "complete",
			Draft: "draft",
			Sent: "waiting",
			"In Progress": "waiting",
			Declined: "declined",
			Expired: "draft",
			Voided: "draft",
		}[status] || "draft"
	);
}
async function pickFile(e) {
	await run(async () => {
		pdfUrl.value = await upload(e.target.files[0]);
		if (!form.value.title) form.value.title = e.target.files[0].name.replace(/\.pdf$/i, "");
		fields.value = [];
		delete form.value.template;
		delete form.value.source_pdf;
	});
}
function addField(type) {
	const field = {
		field_key: crypto.randomUUID(),
		field_type: type,
		label: type,
		signer_role: form.value.signers[0].role_key,
		page: page.value,
		pos_x: 0.12,
		pos_y: 0.6,
		width: type === "Checkbox" ? 0.04 : 0.28,
		height: type === "Signature" ? 0.075 : 0.045,
		required: 1,
		font_size: 12,
	};
	fields.value.push(field);
	selected.value = field;
}
let drag = null;
function beginDrag(e, f) {
	if (e.button !== 0) return;
	selected.value = f;
	drag = {
		field: f,
		startX: e.clientX,
		startY: e.clientY,
		x: f.pos_x,
		y: f.pos_y,
		rect: e.currentTarget.parentElement.getBoundingClientRect(),
	};
	e.currentTarget.setPointerCapture(e.pointerId);
}
function moveDrag(e) {
	if (!drag) return;
	const f = drag.field;
	f.pos_x = Math.max(
		0,
		Math.min(1 - f.width, drag.x + (e.clientX - drag.startX) / drag.rect.width),
	);
	f.pos_y = Math.max(
		0,
		Math.min(1 - f.height, drag.y + (e.clientY - drag.startY) / drag.rect.height),
	);
}
function position(f) {
	return {
		left: f.pos_x * 100 + "%",
		top: f.pos_y * 100 + "%",
		width: f.width * 100 + "%",
		height: f.height * 100 + "%",
	};
}
async function saveDraft() {
	if (!pdfUrl.value) throw new Error("Upload a PDF to continue.");
	if (!fields.value.length) throw new Error("Add at least one signing field.");
	if (!form.value.title.trim()) throw new Error("Give this document a title.");
	const data = {
		...form.value,
		pdf_file: form.value.source_pdf || pdfUrl.value,
		fields: fields.value,
	};
	if (!draftId.value) {
		const d = await api(
			form.value.template ? "envelope.create_from_template" : "envelope.create_adhoc",
			form.value.template ? { template: form.value.template, data } : { data },
		);
		draftId.value = d.name;
		await api("envelope.save_envelope_fields", { name: d.name, fields: fields.value });
	} else {
		await api("envelope.update_envelope", { name: draftId.value, data });
		await api("envelope.save_envelope_fields", { name: draftId.value, fields: fields.value });
	}
	return draftId.value;
}
async function sendDraft() {
	await run(async () => {
		const name = await saveDraft();
		await api("envelope.send_envelope", { name });
		go(root + "/document/" + name);
	});
}
const editingTemplate = ref(null);
async function editTemplate(name) {
	await go(root + "/new");
	await useTemplate(name);
	editingTemplate.value = name;
}
async function templateAction(method, name) {
	await run(async () => {
		await api("template." + method, { name });
		await load();
	});
}
async function openTemplate(name) {
	await go(root + "/new");
	await useTemplate(name);
}
async function useTemplate(name) {
	await run(async () => {
		const t = await api("template.get_template", { name });
		const d = t.template;
		pdfUrl.value = downloadUrl("template.preview_pdf", { name });
		form.value = { ...form.value, ...d };
		form.value.title = d.title;
		form.value.source_pdf = d.pdf_file;
		form.value.signers = d.signer_roles.map((r, i) => ({
			...r,
			signer_name: "",
			signer_email: "",
			role_key: r.role_key,
			role_label: r.role_label,
			signing_order: r.signing_order || i + 1,
		}));
		fields.value = t.fields.map((f) => ({ ...f }));
		form.value.template = name;
	});
}
async function saveTemplate() {
	await run(async () => {
		if (!pdfUrl.value || !fields.value.length)
			throw new Error("Upload a PDF and add fields first.");
		const templateData = { ...form.value };
		const roles = form.value.signers.map((s) => ({
			...s,
			role_label: s.role_label || s.signer_name || "Signer",
			role_key: s.role_key,
			signing_order: s.signing_order,
		}));
		if (editingTemplate.value) {
			const name = editingTemplate.value;
			await api("template.update_template", { name, data: templateData });
			await api("template.set_template_pdf", {
				name,
				file_url: form.value.source_pdf || pdfUrl.value,
			});
			await api("template.save_template_roles", { name, roles });
			await api("template.save_template_fields", { name, fields: fields.value });
			await api("template.publish_template", { name });
			await go(root + "/templates");
			return;
		}
		const d = await api("template.create_template", {
			data: {
				...templateData,
				title: form.value.title,
				pdf_file: form.value.source_pdf || pdfUrl.value,
				signer_roles: form.value.signers.map((s) => ({
					...s,
					role_label: s.role_label || s.signer_name || "Signer",
					role_key: s.role_key,
					signing_order: s.signing_order,
				})),
			},
		});
		await api("template.save_template_fields", { name: d.name, fields: fields.value });
		await api("template.publish_template", { name: d.name });
		go(root + "/templates");
	});
}
async function action(method, args = {}, text = "Saved") {
	await run(async () => {
		await api(method, { name: detail.value.envelope.name, ...args });
		await load();
		flash(text);
	});
}
async function sign() {
	await run(async () => {
		await api("signing.submit", {
			token: token.value,
			values: values.value,
			signature: signature.value,
			consent: consent.value,
		});
		await load();
	});
}
async function decline() {
	await run(async () => {
		await api("signing.decline", { token: token.value, reason: reason.value });
		signContext.value = null;
		flash("You declined this document. The sender will be notified.");
	});
}
function editDraft() {
	const d = detail.value;
	history.pushState({}, "", root + "/new");
	route.value = root + "/new";
	draftId.value = d.envelope.name;
	const reference = JSON.parse(d.envelope.metadata_json || "{}");
	form.value = {
		...d.envelope,
		source_doctype: reference.ref_doctype || "",
		source_name: reference.ref_name || "",
	};
	fields.value = d.fields.map((f) => ({ ...f }));
	pdfUrl.value = d.envelope.source_pdf;
}
onMounted(async () => {
	window.addEventListener("popstate", pop);
	window.addEventListener("keydown", escapeMenu);
	try {
		const r = await fetch("/demo/config");
		if (r.ok) {
			const d = await r.json();
			demo.value = d.demo === true;
		}
	} catch {}
	await load();
});
onBeforeUnmount(() => {
	window.removeEventListener("popstate", pop);
	window.removeEventListener("keydown", escapeMenu);
	clearTimeout(poll);
});
</script>
<template>
	<div v-if="demo" class="preview-banner">
		Local design preview · fictional documents · no email is sent
		<a href="/sign/demo-signer" @click.prevent="go('/sign/demo-signer')"
			>Try signing <ArrowUpRight :size="13"
		/></a>
	</div>
	<div :class="['app', { 'signer-app': isSigner }]">
		<button
			v-if="mobile && !isSigner"
			class="nav-backdrop"
			aria-label="Close navigation"
			@click="mobile = false"
		/>
		<aside v-if="!isSigner" :class="['sidebar', { open: mobile }]">
			<BrandLogo @home="goHome" />
			<button class="text-button mobile-menu" @click="mobile = false">
				Close navigation
			</button>
			<p class="nav-label">Workspace</p>
			<nav aria-label="Main navigation">
				<a
					:class="{ active: ['documents', 'document', 'new'].includes(view) }"
					:href="root"
					@click.prevent="go(root)"
					><FileText :size="18" /> Documents</a
				><a
					:class="{ active: isTemplate }"
					:href="root + '/templates'"
					@click.prevent="
						filter = 'All documents';
						go(root + '/templates');
					"
					><Files :size="18" /> Templates</a
				><a
					:class="{ active: view === 'settings' }"
					:href="root + '/settings'"
					@click.prevent="go(root + '/settings')"
					><Settings :size="18" /> Settings</a
				><a
					:class="{ active: isPending }"
					:href="root + '/my-sign'"
					@click.prevent="go(root + '/my-sign')"
					><PenLine :size="18" /> Awaiting my signature</a
				>
			</nav>
			<div class="sidebar-bottom">
				<button class="text-button" @click="setTheme(theme === 'dark' ? 'light' : 'dark')">
					{{ theme === "dark" ? "Light appearance" : "Dark appearance" }}
				</button>
				<a href="/desk"><ArrowUpRight :size="16" /> Back to ERPNext</a
				><a
					href="https://github.com/joscasjac/nesscale_sign"
					target="_blank"
					rel="noopener"
					>Source & documentation <ExternalLink :size="13"
				/></a>
				<div class="workspace-id">
					<span class="avatar">{{ demo ? "D" : userInitial }}</span
					><span
						>{{ demo ? "Demo workspace" : "Your workspace"
						}}<small>Open E-Sign ERPNext</small></span
					>
				</div>
			</div>
		</aside>
		<main>
			<header class="topbar">
				<button
					v-if="!isSigner"
					class="icon-button mobile-menu"
					aria-label="Open navigation"
					:aria-expanded="mobile"
					@click="mobile = !mobile"
				>
					<Menu :size="20" /></button
				><BrandLogo v-if="isSigner" compact @home="goHome" /><BrandLogo
					v-else
					class="mobile-menu"
					compact
					@home="goHome"
				/><span v-if="!isSigner" class="breadcrumb"
					>Workspace <span>/</span>
					{{
						isTemplate ? "Templates" : view === "settings" ? "Settings" : "Documents"
					}}</span
				><button
					v-if="isSigner"
					class="text-button"
					@click="setTheme(theme === 'dark' ? 'light' : 'dark')"
				>
					{{ theme === "dark" ? "Light" : "Dark" }} appearance</button
				><span class="topbar-note">{{
					isSigner ? "Document signing" : demo ? "Local preview" : "ERPNext workspace"
				}}</span>
			</header>
			<div v-if="error" role="alert" class="error global-message">
				{{ error }} <button class="text-button" @click="load">Reload</button>
			</div>
			<div v-if="notice" role="status" class="notice global-message">{{ notice }}</div>
			<div v-if="loading" class="loading-state" role="status">Loading your workspace…</div>
			<template v-else>
				<section
					v-if="view === 'documents' || isTemplate || isPending"
					class="register content"
				>
					<div class="page-title">
						<div>
							<h1>
								{{
									isTemplate
										? "Templates"
										: isPending
											? "Awaiting my signature"
											: "Documents"
								}}
							</h1>
							<p>
								{{
									isTemplate
										? "Start with a document you use again and again."
										: "Every agreement, from first send to final signature."
								}}
							</p>
						</div>
						<button class="primary" @click="go(root + '/new')">
							<Plus :size="17" />
							{{ isTemplate ? "Create template" : "New document" }}
						</button>
					</div>
					<div v-if="!isTemplate && !isPending" class="summary-line">
						<span
							><i class="dot waiting" /> {{ stats.in_flight || 0 }} waiting for
							signatures</span
						><span
							><i class="dot complete" /> {{ stats.completed || 0 }} completed</span
						><span>{{ stats.counts?.Draft || 0 }} drafts</span>
					</div>
					<ActivitySummary v-if="!isTemplate && !isPending" :stats="stats" />
					<div v-if="!isPending" class="register-tools">
						<div class="tabs" aria-label="Document status">
							<button
								v-for="f in isTemplate
									? ['All documents']
									: [
											'All documents',
											'Waiting for others',
											'In progress',
											'Completed',
											'Drafts',
											'Declined',
											'Expired',
											'Voided',
										]"
								:key="f"
								:class="{ active: filter === f }"
								@click="setFilter(f)"
							>
								{{ isTemplate ? "All templates" : f }}
							</button>
						</div>
						<form class="search" @submit.prevent="search">
							<Search :size="16" /><input
								v-model="query"
								:placeholder="isTemplate ? 'Search templates' : 'Search documents'"
								aria-label="Search documents"
							/><button class="sr-only">Search</button>
						</form>
					</div>
					<div class="table-wrap">
						<table>
							<thead>
								<tr>
									<th>{{ isTemplate ? "Template name" : "Document name" }}</th>
									<th>Status</th>
									<th>{{ isTemplate ? "Pages" : "Sent by" }}</th>
									<th>Last updated</th>
									<th><span class="sr-only">Open document</span></th>
								</tr>
							</thead>
							<tbody>
								<tr v-for="r in rows" :key="r.name">
									<td>
										<a
											class="document-link"
											:href="root + '/document/' + r.name"
											@click.prevent="
												isTemplate
													? openTemplate(r.name)
													: go(
															isPending
																? '/sign/' +
																		encodeURIComponent(r.token)
																: root + '/document/' + r.name,
														)
											"
											><span class="file-icon"><FileText :size="21" /></span
											><span
												>{{ r.title }}<small>{{ r.name }}</small></span
											></a
										>
									</td>
									<td>
										<span :class="['status', statusClass(r.status)]"
											><i />{{ r.status }}</span
										>
									</td>
									<td>{{ isTemplate ? r.page_count : r.sender_name || "—" }}</td>
									<td>{{ date(r.modified) }}</td>
									<td>
										<div v-if="isTemplate" class="template-actions">
											<button @click="editTemplate(r.name)">Edit</button
											><button
												@click="
													templateAction('duplicate_template', r.name)
												"
											>
												Duplicate</button
											><button
												v-if="r.status !== 'Archived'"
												@click="templateAction('archive_template', r.name)"
											>
												Archive
											</button>
										</div>
										<button
											class="icon-button"
											:aria-label="'Open ' + r.title"
											@click="
												isTemplate
													? openTemplate(r.name)
													: go(
															isPending
																? '/sign/' +
																		encodeURIComponent(r.token)
																: root + '/document/' + r.name,
														)
											"
										>
											<ArrowUpRight :size="18" />
										</button>
									</td>
								</tr>
							</tbody>
						</table>
						<div v-if="!rows.length" class="empty">
							<FileText :size="32" />
							<h2>
								{{
									query
										? "No matching documents"
										: isTemplate
											? "Your reusable documents belong here"
											: "Ready for your first signature"
								}}
							</h2>
							<p>
								{{
									query
										? "Try another title or clear your filters."
										: "Upload an existing PDF and choose who needs to sign."
								}}
							</p>
							<button @click="query ? ((query = ''), search()) : go(root + '/new')">
								{{ query ? "Clear search" : "Add a document" }}
							</button>
						</div>
					</div>
					<footer v-if="!isPending" class="table-footer">
						<span
							>{{ rows.length ? `${offset + 1}–${offset + rows.length}` : "0" }}
							{{ isTemplate ? "templates" : "documents" }}</span
						>
						<div>
							<button
								class="icon-button"
								:disabled="offset === 0"
								aria-label="Previous page"
								@click="
									offset -= 20;
									load();
								"
							>
								<ChevronLeft :size="16" /></button
							><button
								class="icon-button"
								:disabled="rows.length < 20"
								aria-label="Next page"
								@click="
									offset += 20;
									load();
								"
							>
								<ChevronRight :size="16" />
							</button>
						</div>
					</footer>
					<div class="quiet-note">
						<span>A clear record, at every step.</span> Signed copies and completion
						records stay with your documents.
					</div>
				</section>
				<section v-else-if="view === 'document' && detail" class="content">
					<button class="text-button back" @click="go(root)">
						<ArrowLeft :size="15" /> Documents
					</button>
					<div class="page-title">
						<div>
							<h1>{{ detail.envelope.title }}</h1>
							<p>
								{{ detail.envelope.name }} ·
								{{ detail.envelope.routing_type }} signing
							</p>
						</div>
						<span :class="['status', statusClass(detail.envelope.status)]"
							><i />{{ detail.envelope.status }}</span
						>
					</div>
					<div class="document-actions">
						<template v-if="detail.envelope.status === 'Draft'"
							><button @click="editDraft">Edit document</button
							><button
								class="primary"
								:disabled="busy"
								@click="action('envelope.send_envelope', {}, 'Document sent')"
							>
								<Send :size="15" /> Send for signature
							</button></template
						><template
							v-else-if="['Sent', 'In Progress'].includes(detail.envelope.status)"
							><button
								:disabled="busy"
								@click="action('envelope.remind_envelope', {}, 'Reminder queued')"
							>
								Send reminder</button
							><button :disabled="busy" @click="declining = !declining">
								Void document
							</button></template
						><template v-if="detail.envelope.status === 'Completed'"
							><a
								class="button primary"
								:href="
									downloadUrl('envelope.download_signed', {
										name: detail.envelope.name,
									})
								"
								><Download :size="15" /> Signed PDF</a
							><a
								class="button"
								:href="
									downloadUrl('envelope.download_certificate', {
										name: detail.envelope.name,
									})
								"
								>Completion record</a
							></template
						>
					</div>
					<form
						v-if="declining"
						class="inline-form"
						@submit.prevent="
							action('envelope.void_envelope', { reason }, 'Document voided');
							declining = false;
						"
					>
						<label>Reason for voiding<input v-model="reason" required /></label
						><button :disabled="busy">Confirm void</button
						><button type="button" @click="declining = false">Cancel</button>
					</form>
					<div v-if="detail.envelope.finalization_status === 'Pending'" class="notice">
						All signatures received. Preparing the completed PDF…
					</div>
					<div v-if="detail.envelope.finalization_status === 'Failed'" class="error">
						{{ detail.envelope.finalization_error
						}}<button
							:disabled="busy"
							@click="action('envelope.retry_completion', {}, 'Completion queued')"
						>
							Retry completion
						</button>
					</div>
					<div class="document-layout">
						<div class="document-stage">
							<div class="page-control">
								<span>Document preview</span>
								<div>
									<button
										class="icon-button"
										aria-label="Previous PDF page"
										:disabled="page <= 1"
										@click="page--"
									>
										<ChevronLeft :size="16" /></button
									>{{ page }} / {{ pages
									}}<button
										class="icon-button"
										aria-label="Next PDF page"
										:disabled="page >= pages"
										@click="page++"
									>
										<ChevronRight :size="16" />
									</button>
								</div>
							</div>
							<PdfPage :url="pdfUrl" :page="page" @loaded="pages = $event" />
						</div>
						<aside class="detail-panel">
							<h2>Recipients</h2>
							<div
								v-for="(s, i) in detail.envelope.signers"
								:key="s.name"
								class="recipient"
							>
								<span class="avatar">{{ i + 1 }}</span>
								<div>
									<strong>{{ s.signer_name }}</strong
									><small>{{ s.signer_email }}</small
									><span
										:class="[
											'status',
											s.status === 'Signed' ? 'complete' : 'waiting',
										]"
										><i />{{ s.status }}</span
									>
								</div>
							</div>
							<h2>Activity</h2>
							<ol class="timeline">
								<li v-for="event in detail.audit" :key="event.name">
									<strong>{{ event.action }}</strong
									><small
										>{{
											event.signer_name || event.signer_email || "Workspace"
										}}
										· {{ date(event.timestamp) }}</small
									>
								</li>
							</ol>
							<div class="integrity-note">
								<h3>Document integrity</h3>
								<p>
									{{
										detail.envelope.seal_status === "Sealed"
											? "A certificate-based PDF seal was applied. Validate its certificate trust in your PDF reader."
											: "Certificate-based PDF sealing is not configured."
									}}
								</p>
								<small v-if="detail.envelope.source_sha256"
									>Original fingerprint recorded at send time.</small
								>
							</div>
						</aside>
					</div>
				</section>
				<section v-else-if="view === 'new'" class="content compose">
					<button class="text-button back" @click="go(root)">
						<ArrowLeft :size="15" /> Documents
					</button>
					<div class="page-title">
						<div>
							<h1>{{ editingTemplate ? "Edit template" : "Prepare a document" }}</h1>
							<p>Choose your PDF, add recipients, then place their fields.</p>
						</div>
						<div class="button-group">
							<button
								v-if="editingTemplate"
								class="primary"
								:disabled="busy"
								@click="saveTemplate"
							>
								Save and publish template</button
							><button
								v-if="!editingTemplate"
								:disabled="busy"
								@click="
									run(async () => {
										const name = await saveDraft();
										go(root + '/document/' + name);
									})
								"
							>
								Save draft</button
							><button
								class="primary"
								:disabled="busy || !pdfUrl"
								@click="sendDraft"
								v-if="!editingTemplate"
							>
								<Send :size="16" /> Send for signature
							</button>
						</div>
					</div>
					<div class="compose-layout">
						<aside class="compose-panel">
							<label
								>Document title<input
									v-model="form.title"
									placeholder="e.g. Service agreement"
									maxlength="140" /></label
							><label class="upload-control"
								><FileText :size="19" />
								{{ pdfUrl ? "Replace PDF" : "Upload a PDF"
								}}<input
									type="file"
									accept="application/pdf"
									@change="pickFile"
									:disabled="busy" /></label
							><small>PDF · up to 15 MB · 100 pages</small
							><label v-if="templates.length"
								>Or use a template<select
									@change="useTemplate($event.target.value)"
								>
									<option value="">Choose a template</option>
									<option v-for="t in templates" :value="t.name">
										{{ t.title }}
									</option>
								</select></label
							>
							<h2>Recipients</h2>
							<div
								class="signer-form"
								v-for="(s, i) in form.signers"
								:key="s.role_key"
							>
								<div class="recipient-title">
									<span>Recipient {{ i + 1 }}</span
									><button
										v-if="form.signers.length > 1"
										class="icon-button"
										:aria-label="'Remove recipient ' + (i + 1)"
										@click="form.signers.splice(i, 1)"
									>
										<Trash2 :size="14" />
									</button>
								</div>
								<label
									>Name<input
										v-model="s.signer_name"
										autocomplete="off"
										placeholder="Full name" /></label
								><label
									>Email<input
										v-model="s.signer_email"
										type="email"
										placeholder="name@company.com"
								/></label>
							</div>
							<button
								class="text-button"
								@click="
									form.signers.push({
										signer_name: '',
										signer_email: '',
										role_key: crypto.randomUUID(),
										signing_order: form.signers.length + 1,
									})
								"
							>
								<Plus :size="14" /> Add recipient</button
							><label
								>ERPNext document type (optional)<input
									v-model="form.source_doctype"
									placeholder="For example, Sales Order" /></label
							><label
								>Document name<input
									v-model="form.source_name"
									placeholder="For example, SAL-ORD-2026-00001" /></label
							><label
								>Signing order<select v-model="form.routing_type">
									<option>Sequential</option>
									<option>Parallel</option>
								</select></label
							><label
								>Expires on (optional)<input
									type="datetime-local"
									v-model="form.expires_on" /></label
							><label>Email subject<input v-model="form.email_subject" /></label
							><label
								>Message to recipients<textarea
									v-model="form.message"
									rows="3"
									placeholder="A short note about this document"
								/></label
							><button :disabled="busy || !pdfUrl" @click="saveTemplate">
								{{
									editingTemplate
										? "Save and publish template"
										: "Save as reusable template"
								}}
							</button>
							<TemplateOptions :form="form" />
						</aside>
						<div class="editor-stage">
							<div class="field-toolbar">
								<span>Add field</span
								><button
									v-for="t in fieldTypes"
									:disabled="!pdfUrl"
									@click="addField(t)"
								>
									{{ t }}
								</button>
							</div>
							<div class="page-control" v-if="pdfUrl">
								<span>Drag a field to position it</span>
								<div>
									<button
										class="icon-button"
										:disabled="page <= 1"
										aria-label="Previous page"
										@click="page--"
									>
										<ChevronLeft :size="16" /></button
									>{{ page }} / {{ pages
									}}<button
										class="icon-button"
										:disabled="page >= pages"
										aria-label="Next page"
										@click="page++"
									>
										<ChevronRight :size="16" />
									</button>
								</div>
							</div>
							<PdfPage
								v-if="pdfUrl"
								:url="pdfUrl"
								:page="page"
								@loaded="pages = $event"
								><button
									v-for="f in fields.filter((x) => x.page === page)"
									:key="f.field_key"
									:class="['placed-field', { selected: selected === f }]"
									:style="position(f)"
									@pointerdown="beginDrag($event, f)"
									@pointermove="moveDrag"
									@pointerup="drag = null"
									@pointercancel="drag = null"
									@click="selected = f"
								>
									{{ f.label || f.field_type }}
								</button></PdfPage
							>
							<div v-else class="empty document-placeholder">
								<FileText :size="40" />
								<h2>Your document starts here</h2>
								<p>
									Upload a PDF using the panel on the left.<br />Its layout stays
									exactly as you created it.
								</p>
							</div>
						</div>
					</div>
					<div v-if="selected" class="field-inspector">
						<strong>Selected field</strong
						><button :disabled="pages < 2 || busy" @click="repeatSelected">
							Repeat on all pages</button
						><button
							@click="
								fields.push({
									...selected,
									name: undefined,
									field_key: crypto.randomUUID(),
									repeat_group: undefined,
								})
							"
						>
							Duplicate field</button
						><label
							>Font size<input
								type="number"
								min="6"
								max="48"
								v-model.number="selected.font_size" /></label
						><label>Prefilled value<input v-model="selected.default_value" /></label
						><label
							>ERP field mapping<input
								v-model="selected.mapping_key"
								placeholder="For example, customer_name" /></label
						><label class="check-label"
							><input
								type="checkbox"
								v-model="selected.read_only"
								:true-value="1"
								:false-value="0"
							/>Read only</label
						><label>Label<input v-model="selected.label" /></label
						><label
							>Recipient<select v-model="selected.signer_role">
								<option v-for="s in form.signers" :value="s.role_key">
									{{ s.signer_name || s.signer_email || "Recipient" }}
								</option>
							</select></label
						><label
							>Left %<input
								type="number"
								min="0"
								max="95"
								:value="Math.round(selected.pos_x * 100)"
								@input="
									selected.pos_x = Math.max(
										0,
										Math.min(
											1 - selected.width,
											Number($event.target.value) / 100,
										),
									)
								" /></label
						><label
							>Top %<input
								type="number"
								min="0"
								max="95"
								:value="Math.round(selected.pos_y * 100)"
								@input="
									selected.pos_y = Math.max(
										0,
										Math.min(
											1 - selected.height,
											Number($event.target.value) / 100,
										),
									)
								" /></label
						><label
							>Width %<input
								type="number"
								min="2"
								max="100"
								:value="Math.round(selected.width * 100)"
								@input="
									selected.width = Math.max(
										0.02,
										Math.min(
											1 - selected.pos_x,
											Number($event.target.value) / 100,
										),
									)
								" /></label
						><label
							>Height %<input
								type="number"
								min="2"
								max="100"
								:value="Math.round(selected.height * 100)"
								@input="
									selected.height = Math.max(
										0.02,
										Math.min(
											1 - selected.pos_y,
											Number($event.target.value) / 100,
										),
									)
								" /></label
						><label v-if="selected.field_type === 'Dropdown'"
							>Options (one per line)<textarea v-model="selected.options" /></label
						><label class="check-label"
							><input
								type="checkbox"
								v-model="selected.required"
								:true-value="1"
								:false-value="0"
							/>
							Required</label
						><button
							class="icon-button"
							aria-label="Delete selected field"
							@click="
								fields = fields.filter((f) => f !== selected);
								selected = null;
							"
						>
							<Trash2 :size="17" />
						</button>
					</div>
				</section>
				<section v-else-if="view === 'settings' && settings" class="content settings">
					<div class="page-title">
						<div>
							<h1>Workspace settings</h1>
							<p>A dependable setup for every document you send.</p>
						</div>
					</div>
					<div class="settings-row">
						<div>
							<h2>Email delivery</h2>
							<p>
								Invitations and reminders use your Frappe outgoing email account.
							</p>
						</div>
						<span
							:class="['status', settings.email_configured ? 'complete' : 'waiting']"
							>{{ settings.email_configured ? "Configured" : "Needs setup" }}</span
						><a class="button" href="/desk/email-account"
							>Manage email <ArrowUpRight :size="14"
						/></a>
					</div>
					<div class="settings-row">
						<div>
							<h2>PDF sealing</h2>
							<p>
								Apply a certificate-based seal to completed PDFs and completion
								records.
							</p>
							<small>{{
								settings.seal_configured
									? "Certificate configured; trust is determined by the validating PDF reader."
									: "Signing works without a seal, but the PDFs are not cryptographically signed."
							}}</small>
						</div>
						<span
							:class="['status', settings.seal_configured ? 'complete' : 'waiting']"
							>{{ settings.seal_configured ? "Configured" : "Not configured" }}</span
						><a
							class="button"
							href="https://github.com/joscasjac/nesscale_sign/blob/codex/open-esign/docs/SECURITY.md"
							target="_blank"
							rel="noopener"
							>Setup guide <ArrowUpRight :size="14"
						/></a>
					</div>
					<div class="settings-row">
						<div>
							<h2>Templates & ERP automation</h2>
							<p>
								Configure document triggers, field mappings and email templates in
								Desk.
							</p>
						</div>
						<a class="button" href="/desk/ns-template"
							>Open template settings <ArrowUpRight :size="14"
						/></a>
					</div>
					<div class="settings-row">
						<div>
							<h2>Organizations & reminder policies</h2>
							<p>
								Manage sender identities, reminder intervals, expiry defaults and
								organization settings.
							</p>
						</div>
						<a class="button" href="/desk/ns-organization"
							>Manage organizations <ArrowUpRight :size="14"
						/></a>
					</div>
					<div class="settings-row">
						<div>
							<h2>Email templates</h2>
							<p>
								Edit the invitations, reminders and completion emails used by the
								signing workflow.
							</p>
						</div>
						<a class="button" href="/desk/email-template"
							>Edit email templates <ArrowUpRight :size="14"
						/></a>
					</div>
					<div class="settings-row">
						<div>
							<h2>Application settings</h2>
							<p>
								Default organization, support address, sender address and public
								signing URL.
							</p>
						</div>
						<a class="button" href="/desk/ns-settings"
							>Open application settings <ArrowUpRight :size="14"
						/></a>
					</div>
					<div class="settings-row">
						<div>
							<h2>Open source</h2>
							<p>
								Open E-Sign ERPNext builds on Nesscale Sign by Nesscale Solutions.
							</p>
							<small
								>AGPL-3.0 · Full source for this fork is publicly available.</small
							>
						</div>
						<a
							class="button"
							href="https://github.com/joscasjac/nesscale_sign"
							target="_blank"
							rel="noopener"
							>View source <ExternalLink :size="14"
						/></a>
					</div>
				</section>
				<section v-else-if="isSigner && signContext" class="sign-content">
					<div class="page-title">
						<div>
							<p class="sender-line">
								{{ signContext.envelope.sender_name }} has shared a document with
								you
							</p>
							<h1>{{ signContext.envelope.title }}</h1>
							<p>
								{{
									signContext.envelope.message ||
									"Please review the document before signing."
								}}
							</p>
						</div>
					</div>
					<div
						v-if="signContext.envelope.status === 'Completed'"
						class="completed-banner"
					>
						<Check :size="28" />
						<div>
							<h2>All signed. You’re done.</h2>
							<p>A copy is ready for your records.</p>
						</div>
						<a
							class="button primary"
							:href="downloadUrl('signing.download_completed', { token })"
							><Download :size="16" /> Download PDF</a
						>
					</div>
					<div v-else-if="signContext.signer.status === 'Signed'" class="notice">
						Your signature is saved.
						{{
							signContext.envelope.finalization_status === "Pending"
								? "We’re preparing the final document."
								: "You’ll receive a copy when everyone has signed."
						}}
					</div>
					<div class="sign-layout">
						<div class="document-stage">
							<div class="page-control">
								<a :href="signContext.pdf_url" target="_blank" rel="noopener"
									>Open original PDF <ArrowUpRight :size="12"
								/></a>
								<div>
									<button
										class="icon-button"
										:disabled="page <= 1"
										aria-label="Previous PDF page"
										@click="page--"
									>
										<ChevronLeft :size="16" /></button
									>{{ page }} / {{ pages
									}}<button
										class="icon-button"
										:disabled="page >= pages"
										aria-label="Next PDF page"
										@click="page++"
									>
										<ChevronRight :size="16" />
									</button>
								</div>
							</div>
							<PdfPage
								:url="signContext.pdf_url"
								:page="page"
								@loaded="pages = $event"
								><span
									v-for="f in signContext.fields.filter((f) => f.page === page)"
									:key="f.field_key"
									:class="['placed-field', 'sign-preview-field']"
									:style="position(f)"
									>{{ values[f.field_key] || f.label }}</span
								></PdfPage
							>
						</div>
						<aside class="sign-panel">
							<h2>Your details</h2>
							<p class="muted">
								Signing as {{ signContext.signer.name }}<br />{{
									signContext.signer.email
								}}
							</p>
							<form v-if="signContext.signer.can_sign" @submit.prevent="sign">
								<template v-for="f in ownFields" :key="f.field_key"
									><label
										v-if="
											!['Signature', 'Initial', 'Stamp'].includes(
												f.field_type,
											)
										"
										>{{ f.label || f.field_type }} {{ f.required ? "*" : ""
										}}<select
											v-if="f.field_type === 'Dropdown'"
											v-model="values[f.field_key]"
											:required="!!f.required"
										>
											<option value="">Select an option</option>
											<option
												v-for="o in (f.options || '').split('\n')"
												:value="o"
											>
												{{ o }}
											</option></select
										><input
											v-else-if="f.field_type === 'Checkbox'"
											type="checkbox"
											v-model="values[f.field_key]"
											true-value="1"
											false-value=""
											:required="!!f.required" /><input
											v-else
											v-model="values[f.field_key]"
											:required="!!f.required"
											maxlength="10000" /></label
								></template>
								<h3
									v-if="
										ownFields.some((f) =>
											['Signature', 'Initial', 'Stamp'].includes(
												f.field_type,
											),
										)
									"
								>
									Your signature
								</h3>
								<SignaturePad
									v-if="
										ownFields.some((f) =>
											['Signature', 'Initial', 'Stamp'].includes(
												f.field_type,
											),
										)
									"
									@change="signature = $event"
								/><label class="check-label consent"
									><input type="checkbox" v-model="consent" required /><span>{{
										signContext.consent_text
									}}</span></label
								><button
									class="primary full"
									:disabled="busy || !consent || requiredRemaining > 0"
								>
									<Check :size="17" />
									{{ busy ? "Saving signature…" : "Agree & sign" }}
								</button>
								<p class="sign-footnote">
									{{
										requiredRemaining
											? `${requiredRemaining} required fields remaining`
											: "Your completed copy will be available after everyone signs."
									}}
								</p>
								<button
									type="button"
									class="text-button"
									@click="declining = !declining"
								>
									Decline to sign
								</button>
							</form>
							<p v-else-if="signContext.signer.status !== 'Signed'" class="muted">
								You’ll be notified when it’s your turn to sign.
							</p>
							<form v-if="declining" class="decline-form" @submit.prevent="decline">
								<label
									>Reason (optional)<textarea v-model="reason" rows="3" /></label
								><button :disabled="busy">Confirm decline</button
								><button type="button" @click="declining = false">Cancel</button>
							</form>
						</aside>
					</div>
					<footer class="sign-footer">
						Powered by Open E-Sign ERPNext
						<a
							href="https://github.com/joscasjac/nesscale_sign"
							target="_blank"
							rel="noopener"
							>Open-source software</a
						>
					</footer>
				</section>
			</template>
		</main>
	</div>
</template>
