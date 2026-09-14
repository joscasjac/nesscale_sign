<script setup>
import { ref, onMounted, nextTick, watch, onBeforeUnmount } from "vue";
import EditorButton from "./EditorButton.vue";
import { api } from "../api";
const props = defineProps({ modelValue: Object, primary: String, fields: Array });
const emit = defineEmits(["update:modelValue", "update:primary"]);
const error = ref(""),
	contacts = ref([]),
	query = ref(""),
	choosing = ref(false),
	creating = ref(false),
	busy = ref(false),
	name = ref(""),
	email = ref(""),
	replaceRole = ref(null);
const contactDialog = ref(null),
	choosingPrimary = ref(false);
let searchTimer,
	searchVersion = 0;
watch(query, () => {
	clearTimeout(searchTimer);
	searchTimer = setTimeout(search, 200);
});
onBeforeUnmount(() => clearTimeout(searchTimer));
async function openCreate() {
	creating.value = true;
	await nextTick();
	contactDialog.value.showModal();
}
function openPicker(role = null, asPrimary = false) {
	choosingPrimary.value = asPrimary;
	replaceRole.value = role;
	choosing.value = !choosing.value || !!role;
	query.value = "";
	search();
}
function chooseContact(c) {
	const existing = props.modelValue.signers.find(
		(s) => s.contact === c.name || s.signer_email === c.email_id,
	);
	if (existing && !replaceRole.value && choosingPrimary.value) {
		emit("update:primary", existing.role_key);
		choosing.value = false;
	} else select(c);
}
function set(values) {
	emit("update:modelValue", { ...props.modelValue, ...values });
}
async function search() {
	const version = ++searchVersion;
	busy.value = true;
	error.value = "";
	try {
		const result = await api("contacts.search_contacts", { query: query.value });
		if (version === searchVersion) contacts.value = result;
	} catch (e) {
		error.value = e.message;
	} finally {
		if (version === searchVersion) busy.value = false;
	}
}
onMounted(search);
function select(c) {
	if (!c.email_id) {
		error.value = "This contact needs an email address before they can sign.";
		return;
	}
	const all = [...props.modelValue.signers];
	if (!replaceRole.value) replaceRole.value = all.find((s) => !s.signer_email)?.role_key || null;
	if (all.some((s) => s.signer_email === c.email_id && s.role_key !== replaceRole.value)) {
		error.value = "This contact is already a recipient.";
		return;
	}
	const role = replaceRole.value || crypto.randomUUID(),
		signer = {
			role_key: role,
			signer_name: c.full_name,
			signer_email: c.email_id,
			contact: c.name,
			signing_order: all.length + 1,
		};
	set({
		signers: replaceRole.value
			? all.map((s) =>
					s.role_key === role ? { ...signer, signing_order: s.signing_order } : s,
				)
			: [...all, signer],
	});
	if (!props.primary || choosingPrimary.value) emit("update:primary", role);
	choosing.value = false;
	replaceRole.value = null;
	error.value = "";
}
async function create() {
	busy.value = true;
	error.value = "";
	try {
		const c = await api("contacts.create_contact", {
			full_name: name.value,
			email_id: email.value,
		});
		contacts.value.unshift(c);
		select(c);
		creating.value = false;
		name.value = "";
		email.value = "";
	} catch (e) {
		error.value = e.message;
	} finally {
		busy.value = false;
	}
}
function remove(role) {
	if (props.fields?.some((f) => f.signer_role === role)) {
		error.value = "Reassign or remove this recipient’s fields before removing them.";
		return;
	}
	error.value = "";
	set({
		signers: props.modelValue.signers
			.filter((s) => s.role_key !== role)
			.map((s, i) => ({ ...s, signing_order: i + 1 })),
	});
	if (props.primary === role) emit("update:primary", null);
}
function reorder(role, to) {
	const all = [...props.modelValue.signers],
		from = all.findIndex((s) => s.role_key === role);
	if (from < 0 || to < 0 || to >= all.length) return;
	all.splice(to, 0, all.splice(from, 1)[0]);
	set({ signers: all.map((s, i) => ({ ...s, signing_order: i + 1 })) });
}
</script>
<template>
	<div class="recipient-panel">
		<h2>Recipients</h2>
		<p v-if="error" class="error" role="alert">{{ error }}</p>
		<label class="routing-toggle"
			><input
				type="checkbox"
				role="switch"
				:checked="modelValue.routing_type === 'Sequential'"
				@change="set({ routing_type: $event.target.checked ? 'Sequential' : 'Parallel' })"
			/><span
				>Set signing order<small>{{
					modelValue.routing_type === "Sequential"
						? "Each recipient signs after the previous person completes their action."
						: "All recipients can sign at the same time."
				}}</small></span
			></label
		>
		<p v-if="modelValue.routing_type === 'Sequential'" class="routing-hint">
			Drag recipients to change the order.
		</p>
		<div class="contact-picker-shell">
			<label class="primary-contact">Primary contact</label>
			<button
				class="contact-picker-trigger"
				:aria-expanded="choosing"
				aria-label="Choose primary contact"
				@click="openPicker(null, true)"
			>
				<span>{{
					modelValue.signers.find((s) => s.role_key === primary)?.signer_name ||
					modelValue.signers.find((s) => s.signer_email)?.signer_name ||
					"Select a contact"
				}}</span
				><span aria-hidden="true">⌄</span>
			</button>
			<div v-if="choosing" class="contact-dropdown" @keydown.esc.stop="choosing = false">
				<input
					v-model="query"
					type="search"
					aria-label="Filter ERPNext contacts"
					placeholder="Search contacts…"
				/>
				<div
					class="contact-options"
					role="group"
					aria-label="ERPNext contacts"
					:aria-busy="busy"
				>
					<button
						v-for="c in contacts"
						:key="c.name"
						class="contact-option"
						:disabled="!c.email_id"
						@click="chooseContact(c)"
					>
						<strong>{{ c.full_name }}</strong
						><small>{{ c.email_id || "No email address" }}</small>
					</button>
					<p v-if="!contacts.length">
						{{ busy ? "Loading contacts…" : "No matching contacts." }}
					</p>
				</div>
				<button class="create-contact-action" @click="openCreate">
					＋ Add new contact
				</button>
			</div>
		</div>
		<div
			v-for="(s, i) in modelValue.signers.filter((s) => s.signer_email)"
			:key="s.role_key"
			class="recipient-card"
			@dragover.prevent
			@drop.prevent="reorder($event.dataTransfer.getData('application/x-recipient'), i)"
		>
			<div class="recipient-summary">
				<button
					class="recipient-grip"
					:aria-label="'Reorder recipient ' + (i + 1)"
					draggable="true"
					@dragstart="$event.dataTransfer.setData('application/x-recipient', s.role_key)"
					@keydown.up.prevent="reorder(s.role_key, i - 1)"
					@keydown.down.prevent="reorder(s.role_key, i + 1)"
				>
					<span>{{ i + 1 }}</span
					>⠿</button
				><span class="recipient-avatar">{{
					s.signer_name
						.split(" ")
						.map((w) => w[0])
						.slice(0, 2)
						.join("")
				}}</span>
				<div class="recipient-identity">
					<strong>{{ s.signer_name }}</strong
					><small>{{ s.signer_email }}</small>
					<div class="recipient-badges">
						<span v-if="(primary || modelValue.signers[0]?.role_key) === s.role_key"
							>Primary</span
						><span>Needs to sign</span>
					</div>
				</div>
				<EditorButton
					:label="'Change recipient ' + (i + 1)"
					icon="Pencil"
					@click="openPicker(s.role_key)"
				/><EditorButton
					:label="'Remove recipient ' + (i + 1)"
					icon="Trash2"
					@click="remove(s.role_key)"
				/>
			</div>
		</div>
		<button class="add-recipient" @click="openPicker()">＋ Add recipient</button>
		<Teleport to="body">
			<dialog
				v-if="creating"
				ref="contactDialog"
				class="contact-create-dialog"
				aria-labelledby="contact-dialog-title"
				@cancel.prevent="creating = false"
			>
				<div class="dialog-heading">
					<h2 id="contact-dialog-title">Add contact</h2>
					<EditorButton label="Close contact form" icon="X" @click="creating = false" />
				</div>
				<p>Create an ERPNext contact and add them to this document.</p>
				<form class="new-contact" @submit.prevent="create">
					<label
						>Full name<input
							v-model="name"
							required
							maxlength="140"
							autocomplete="name"
							autofocus
					/></label>
					<label
						>Email<input v-model="email" type="email" required autocomplete="email"
					/></label>
					<p v-if="error" class="error" role="alert">{{ error }}</p>
					<footer>
						<button type="button" @click="creating = false">Cancel</button
						><button class="primary" :disabled="busy">
							{{ busy ? "Creating…" : "Create and select" }}
						</button>
					</footer>
				</form>
			</dialog>
		</Teleport>
	</div>
</template>
