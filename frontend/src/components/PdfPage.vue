<script setup>
import { ref, watch, onBeforeUnmount } from "vue";
import { getDocument, GlobalWorkerOptions } from "pdfjs-dist";
import worker from "pdfjs-dist/build/pdf.worker.min.mjs?url";
GlobalWorkerOptions.workerSrc = worker;
const props = defineProps({ url: String, page: { type: Number, default: 1 } });
const emit = defineEmits(["loaded"]);
const readableText = ref("");
const canvas = ref(null),
	error = ref(""),
	loading = ref(true);
let task,
	render,
	version = 0;
watch(
	() => [props.url, props.page, canvas.value],
	async () => {
		if (!props.url || !canvas.value) return;
		const current = ++version;
		error.value = "";
		loading.value = true;
		try {
			render?.cancel();
			await task?.destroy();
			task = getDocument({ url: props.url, withCredentials: true });
			const pdf = await task.promise;
			if (current !== version) return;
			const page = await pdf.getPage(props.page);
			readableText.value = (await page.getTextContent()).items.map((i) => i.str).join(" ");
			const viewport = page.getViewport({ scale: 1.5 });
			canvas.value.width = viewport.width;
			canvas.value.height = viewport.height;
			render = page.render({ canvasContext: canvas.value.getContext("2d"), viewport });
			await render.promise;
			if (current === version) {
				emit("loaded", pdf.numPages);
				loading.value = false;
			}
		} catch (e) {
			if (current === version && e.name !== "RenderingCancelledException") {
				error.value = "This PDF could not be displayed. Reload the document to try again.";
				loading.value = false;
			}
		}
	},
	{ flush: "post" },
);
onBeforeUnmount(() => {
	version++;
	render?.cancel();
	task?.destroy();
});
</script>
<template>
	<div class="pdf-render">
		<p v-if="loading" class="pdf-loading" role="status">Loading document…</p>
		<p v-if="error" role="alert" class="error">{{ error }}</p>
		<canvas ref="canvas" aria-label="Document page" />
		<p class="sr-only" aria-label="Document page text">{{ readableText }}</p>
		<slot v-if="!loading && !error" />
	</div>
</template>
