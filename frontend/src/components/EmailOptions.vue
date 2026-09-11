<script setup>
import { ref, onMounted } from "vue";
import { api } from "../api";
const props = defineProps({ modelValue: Object });
const emit = defineEmits(["update:modelValue"]);
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
		set("email_template", template.name);
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
		<h2>Invitation email</h2>
		<p class="muted">Use a template, or write a subject and body for this document.</p>
		<label
			>Email template<select
				:value="modelValue.email_template || ''"
				@change="set('email_template', $event.target.value)"
			>
				<option value="">Default invitation</option>
				<option v-for="t in templates" :value="t.name">{{ t.name }}</option>
			</select></label
		>
		<label
			>Subject override<input
				:value="modelValue.email_subject"
				maxlength="200"
				placeholder="Use template subject"
				@input="set('email_subject', $event.target.value)"
		/></label>
		<label
			>Body override<textarea
				:value="modelValue.email_message"
				maxlength="20000"
				rows="7"
				placeholder="Use template body"
				@input="set('email_message', $event.target.value)"
			/>
		</label>
		<small
			>Overrides apply only to this invitation. The secure signing link is always added. Mail
			uses your configured Frappe sending account.</small
		>
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
		<details>
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
