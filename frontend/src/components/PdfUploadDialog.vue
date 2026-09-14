<script setup>
import { ref, onMounted } from "vue";
import EditorButton from "./EditorButton.vue";
import { upload, api } from "../api";
const emit = defineEmits(["close", "uploaded"]);
const dialog = ref(null),
	files = ref([]),
	error = ref(""),
	busy = ref(false);
onMounted(() => dialog.value.showModal());
function add(list) {
	error.value = "";
	const incoming = [...list];
	if (incoming.some((f) => !f.name.toLowerCase().endsWith(".pdf"))) {
		error.value = "Only PDF files are supported.";
		return;
	}
	if (
		files.value.length + incoming.length > 10 ||
		[...files.value, ...incoming].reduce((n, f) => n + f.size, 0) > 15 * 1024 * 1024
	) {
		error.value = "Choose up to 10 PDFs totaling 15 MB or less.";
		return;
	}
	files.value.push(...incoming);
}
function move(from, to) {
	if (to < 0 || to >= files.value.length) return;
	files.value.splice(to, 0, files.value.splice(from, 1)[0]);
}
async function submit() {
	busy.value = true;
	error.value = "";
	try {
		const urls = [];
		for (const file of files.value) urls.push(await upload(file));
		const result = await api("builder.combine_pdfs", { urls });
		emit("uploaded", { ...result, title: files.value[0].name.replace(/\.pdf$/i, "") });
	} catch (e) {
		error.value = e.message;
	} finally {
		busy.value = false;
	}
}
</script>
<template>
	<dialog ref="dialog" class="pdf-upload-dialog" @cancel.prevent="!busy && emit('close')">
		<div class="dialog-heading">
			<h2>Upload files</h2>
			<EditorButton label="Close upload" icon="X" :disabled="busy" @click="emit('close')" />
		</div>
		<p>Upload and rearrange files for this document.</p>
		<label
			class="pdf-drop-zone"
			@dragover.prevent
			@drop.prevent="add($event.dataTransfer.files)"
			><span class="upload-symbol">↑</span><span>Click or drag files here to upload</span
			><small>PDF · up to 10 files · 15 MB total · 100 pages</small
			><input
				class="visually-hidden-file"
				aria-label="Choose PDF files"
				type="file"
				multiple
				accept="application/pdf"
				:disabled="busy"
				@change="add($event.target.files)"
		/></label>
		<div
			v-for="(file, i) in files"
			class="upload-file-row"
			draggable="true"
			@dragstart="$event.dataTransfer.setData('text/plain', String(i))"
			@dragover.prevent
			@drop.prevent="move(Number($event.dataTransfer.getData('text/plain')), i)"
		>
			<EditorButton
				label="Move PDF up"
				icon="ArrowUp"
				:disabled="i === 0 || busy"
				@click="move(i, i - 1)"
			/>
			<div>
				<strong>{{ file.name }}</strong
				><small>{{ Math.round(file.size / 1024) }} KB</small>
			</div>
			<EditorButton
				:label="'Remove ' + file.name"
				icon="Trash2"
				:disabled="busy"
				@click="files.splice(i, 1)"
			/>
		</div>
		<p v-if="error" class="error" role="alert">{{ error }}</p>
		<footer>
			<button :disabled="busy" @click="emit('close')">Cancel</button
			><button class="primary" :disabled="busy || !files.length" @click="submit">
				{{ busy ? "Uploading…" : "Upload" }}
			</button>
		</footer>
	</dialog>
</template>
