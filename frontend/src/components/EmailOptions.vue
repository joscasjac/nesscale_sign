<script setup>
import { ref, onMounted } from "vue";
import VariableInput from "./VariableInput.vue";
import { api } from "../api";
const props = defineProps({ modelValue: Object, variables: Array });
const emit = defineEmits(["update:modelValue"]);
const senders = ref([]);
const mode = ref(
	(props.modelValue.email_mode === "custom" ? "custom" : props.modelValue.email_template) ||
		(props.modelValue.email_subject || props.modelValue.email_message
			? "custom"
			: props.modelValue.email_template || "default"),
);
function chooseMode(value) {
	mode.value = value;
	emit("update:modelValue", {
		...props.modelValue,
		email_mode: value === "custom" ? "custom" : "template",
		email_template: ["custom", "default"].includes(value) ? null : value,
		email_subject: "",
		email_message: "",
	});
}
const templates = ref([]),
	error = ref(""),
	busy = ref(false),
	templateName = ref(""),
	files = ref([]);
function set(key, value) {
	emit("update:modelValue", { ...props.modelValue, [key]: value });
}
async function reload() {
	try {
		templates.value = await api("mail.list_templates");
	} catch (e) {
		error.value = e.message;
	}
}
onMounted(async () => {
	await reload();
	try {
		senders.value = await api("mail.list_senders");
		files.value = await api("mail.list_attachments", {
			names: props.modelValue.email_attachments || "[]",
		});
	} catch (e) {
		error.value = e.message;
	}
});
async function attach(e) {
	const file = e.target.files?.[0];
	if (!file) return;
	error.value = "";
	if (file.size > 10 * 1024 * 1024 || files.value.length >= 5) {
		error.value = "Choose at most five files, totaling 10 MB or less.";
		return;
	}
	busy.value = true;
	try {
		const body = new FormData();
		body.append("file", file);
		body.append("is_private", "1");
		const response = await fetch("/api/method/upload_file", {
			method: "POST",
			credentials: "same-origin",
			headers: { "X-Frappe-CSRF-Token": window.csrf_token || "" },
			body,
		});
		const result = await response.json();
		if (!response.ok || !result.message?.name) throw Error("Attachment upload failed.");
		files.value.push({ name: result.message.name, file_name: file.name });
		set("email_attachments", JSON.stringify(files.value.map((f) => f.name)));
	} catch (e) {
		error.value = e.message;
	} finally {
		busy.value = false;
	}
}
function remove(name) {
	files.value = files.value.filter((f) => f.name !== name);
	set("email_attachments", JSON.stringify(files.value.map((f) => f.name)));
}
async function saveTemplate() {
	busy.value = true;
	error.value = "";
	try {
		const template = await api("mail.create_template", {
			name: templateName.value,
			subject: props.modelValue.email_subject || "",
			body: props.modelValue.email_message || "",
		});
		await reload();
		chooseMode(template.name);
		templateName.value = "";
	} catch (e) {
		error.value = e.message;
	} finally {
		busy.value = false;
	}
}
</script>
<template>
	<div class="email-options">
		<label
			>From name<input
				:value="modelValue.email_from_name"
				placeholder="Configured sender name"
				@input="set('email_from_name', $event.target.value)"
		/></label>
		<label
			>From email<select
				:value="modelValue.email_from_account || ''"
				@change="set('email_from_account', $event.target.value)"
			>
				<option value="">Default sending account</option>
				<option v-for="s in senders" :value="s.name">{{ s.email_id }}</option>
			</select></label
		>

		<label
			>Email template<select :value="mode" @change="chooseMode($event.target.value)">
				<option value="default">Default invitation</option>
				<option value="custom">Custom</option>
				<option v-for="t in templates" :value="t.name">{{ t.name }}</option>
			</select></label
		>
		<a class="button" href="/desk/email-template" target="_blank" rel="noopener">Manage email templates in Desk</a>
		<VariableInput
			v-if="mode === 'custom'"
			label="Email subject"
			:model-value="modelValue.email_subject"
			:variables="variables"
			maxlength="200"
			placeholder="Enter an email subject"
			@update:model-value="set('email_subject', $event)"
		/>
		<VariableInput
			v-if="mode === 'custom'"
			label="Email body"
			:model-value="modelValue.email_message"
			:variables="variables"
			multiline
			maxlength="20000"
			placeholder="Write your invitation"
			@update:model-value="set('email_message', $event)"
		/>
		<small
			>The secure signing link is always added. Mail uses your configured Frappe sending
			account.</small
		>
		<div class="completion-settings">
			<label class="routing-toggle"
				><input
					type="checkbox"
					role="switch"
					:checked="
						modelValue.completion_redirect_url !== undefined &&
						modelValue.completion_redirect_url !== null
					"
					@change="set('completion_redirect_url', $event.target.checked ? '' : null)"
				/><span>Redirect after signing</span></label
			><template
				v-if="
					modelValue.completion_redirect_url !== undefined &&
					modelValue.completion_redirect_url !== null
				"
				><label
					>Custom URL<input
						type="url"
						:value="modelValue.completion_redirect_url"
						placeholder="https://example.com/thank-you"
						@input="set('completion_redirect_url', $event.target.value)" /></label
				><label
					>Open in<select
						:value="modelValue.completion_redirect_target || 'Same tab'"
						@change="set('completion_redirect_target', $event.target.value)"
					>
						<option>Same tab</option>
						<option>New tab</option>
					</select></label
				></template
			>
		</div>
		<h3>Attachments</h3>
		<p class="muted">
			Supporting files sent to every invited signer. These are separate from the document
			they sign.
		</p>
		<label class="upload-control"
			>+ Add attachment<input type="file" :disabled="busy" @change="attach" /></label
		><small>Up to 5 files · 10 MB total</small>
		<ul class="attachment-list">
			<li v-for="file in files">
				<span>{{ file.file_name }}</span
				><button @click="remove(file.name)" :aria-label="'Remove ' + file.file_name">
					×
				</button>
			</li>
		</ul>
		<details v-if="mode === 'custom'">
			<summary>Save wording as a template</summary>
			<label>Template name<input v-model="templateName" /></label
			><button
				:disabled="
					busy ||
					!templateName.trim() ||
					!modelValue.email_subject ||
					!modelValue.email_message
				"
				@click="saveTemplate"
			>
				Save email template</button
			><small>Requires permission to create Frappe Email Templates.</small>
		</details>
		<p v-if="error" role="alert" class="error">{{ error }}</p>
	</div>
</template>
