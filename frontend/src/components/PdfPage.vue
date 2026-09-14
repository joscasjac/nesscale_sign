<script setup>
import { ref, shallowRef, watch, onMounted, onBeforeUnmount, nextTick } from "vue";
import { acquirePdf } from "../pdf-cache";
const props = defineProps({ url: String, page: { type: Number, default: 1 }, lazy: Boolean });
const emit = defineEmits(["loaded"]);
const root = ref(null),
	canvas = ref(null),
	readableText = ref(""),
	error = ref(""),
	loading = ref(true),
	visible = ref(!props.lazy),
	ratio = ref(595 / 842),
	pdfPage = shallowRef(null);
let handle,
	render,
	version = 0,
	observer;
watch(
	() => [props.url, props.page],
	async () => {
		const generation = ++version;
		render?.cancel();
		handle?.release();
		handle = null;
		pdfPage.value = null;
		if (!props.url) return;
		loading.value = true;
		error.value = "";
		try {
			handle = acquirePdf(props.url);
			const pdf = await handle.promise;
			if (generation !== version) return;
			const page = await pdf.getPage(props.page);
			if (generation !== version) return;
			const vp = page.getViewport({ scale: 1 });
			ratio.value = vp.width / vp.height;
			pdfPage.value = page;
			emit("loaded", pdf.numPages);
		} catch (e) {
			if (generation === version) {
				error.value = "This PDF could not be displayed. Reload to try again.";
				loading.value = false;
			}
		}
	},
	{ immediate: true },
);
watch(
	() => [pdfPage.value, visible.value, canvas.value],
	async () => {
		render?.cancel();
		if (!pdfPage.value || !visible.value || !canvas.value) return;
		const page = pdfPage.value,
			target = canvas.value,
			generation = version;
		loading.value = true;
		try {
			await nextTick();
			const viewport = page.getViewport({
				scale: Math.min(1.5, 1190 / page.getViewport({ scale: 1 }).width),
			});
			target.width = viewport.width;
			target.height = viewport.height;
			render = page.render({ canvasContext: target.getContext("2d"), viewport });
			await render.promise;
			if (generation !== version) return;
			readableText.value = (await page.getTextContent()).items.map((i) => i.str).join(" ");
			loading.value = false;
		} catch (e) {
			if (e.name !== "RenderingCancelledException" && generation === version) {
				error.value = "This PDF could not be displayed. Reload to try again.";
				loading.value = false;
			}
		}
	},
	{ flush: "post" },
);
onMounted(() => {
	if (props.lazy) {
		observer = new IntersectionObserver(
			(entries) => (visible.value = entries[0].isIntersecting),
			{ rootMargin: "300px" },
		);
		observer.observe(root.value);
	}
});
onBeforeUnmount(() => {
	version++;
	observer?.disconnect();
	render?.cancel();
	handle?.release();
});
</script>
<template>
	<div ref="root" class="pdf-render" :style="{ aspectRatio: ratio }">
		<p v-if="loading && visible" class="pdf-loading" role="status">Loading document…</p>
		<p v-if="error" role="alert" class="error">{{ error }}</p>
		<canvas v-if="visible" ref="canvas" aria-label="Document page" />
		<p class="sr-only" aria-label="Document page text">{{ readableText }}</p>
		<slot v-if="!loading && !error" />
	</div>
</template>
