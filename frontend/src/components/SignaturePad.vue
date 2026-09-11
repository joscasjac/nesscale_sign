<script setup>
import { ref, onMounted } from "vue";
const props = defineProps({ initialName: { type: String, default: "" } });
const emit = defineEmits(["change"]);
const uploadError = ref("");
const canvas = ref(null),
	mode = ref("Type"),
	name = ref(props.initialName);
let drawing = false;
function ctx() {
	return canvas.value.getContext("2d");
}
function clear() {
	ctx().clearRect(0, 0, 700, 180);
	emit("change", null);
}
function type() {
	clear();
	if (!name.value.trim()) return;
	const c = ctx();
	c.fillStyle = "#24362d";
	c.font = "italic 48px Georgia";
	c.fillText(name.value, 22, 112, 650);
	send();
}
function point(e) {
	const r = canvas.value.getBoundingClientRect();
	return [((e.clientX - r.left) * 700) / r.width, ((e.clientY - r.top) * 180) / r.height];
}
function start(e) {
	if (mode.value !== "Draw") return;
	drawing = true;
	canvas.value.setPointerCapture(e.pointerId);
	ctx().beginPath();
	ctx().moveTo(...point(e));
}
function move(e) {
	if (!drawing) return;
	ctx().lineWidth = 2.4;
	ctx().lineCap = "round";
	ctx().strokeStyle = "#24362d";
	ctx().lineTo(...point(e));
	ctx().stroke();
}
function stop() {
	if (drawing) {
		drawing = false;
		send();
	}
}
function send() {
	emit("change", {
		type: mode.value,
		text: name.value,
		image: canvas.value.toDataURL("image/png"),
	});
}
async function uploadSignature(event) {
	uploadError.value = "";
	clear();
	const file = event.target.files?.[0];
	if (!file) return;
	if (!["image/png", "image/jpeg"].includes(file.type) || file.size > 2 * 1024 * 1024) {
		uploadError.value = "Choose a PNG or JPG smaller than 2 MB.";
		return;
	}
	const url = URL.createObjectURL(file);
	try {
		const image = new Image();
		image.src = url;
		await image.decode();
		const scale = Math.min(660 / image.width, 150 / image.height);
		ctx().drawImage(
			image,
			(700 - image.width * scale) / 2,
			(180 - image.height * scale) / 2,
			image.width * scale,
			image.height * scale,
		);
		send();
	} catch {
		uploadError.value = "This image could not be opened. Choose another PNG or JPG.";
	} finally {
		URL.revokeObjectURL(url);
	}
}
onMounted(() => {
	if (name.value.trim()) type();
	else clear();
});
</script>
<template>
	<div class="signature-pad">
		<div class="tabs compact">
			<button
				type="button"
				:class="{ active: mode === 'Type' }"
				@click="
					mode = 'Type';
					type();
				"
			>
				Type signature</button
			><button
				type="button"
				:class="{ active: mode === 'Draw' }"
				@click="
					mode = 'Draw';
					clear();
				"
			>
				Draw signature
			</button>
			<button
				type="button"
				:class="{ active: mode === 'Upload' }"
				@click="
					mode = 'Upload';
					clear();
				"
			>
				Upload signature
			</button>
		</div>
		<label v-if="mode === 'Upload'"
			>Signature image<input
				type="file"
				accept="image/png,image/jpeg"
				@change="uploadSignature"
			/><small>PNG or JPG, up to 2 MB</small></label
		>
		<p v-if="uploadError" role="alert">{{ uploadError }}</p>
		<label v-if="mode === 'Type'"
			>Full name<input
				v-model="name"
				@input="type"
				placeholder="Your full name"
				autocomplete="name"
				maxlength="100" /></label
		><canvas
			ref="canvas"
			width="700"
			height="180"
			:class="{ drawing: mode === 'Draw' }"
			aria-label="Signature preview; choose Type signature for keyboard entry"
			@pointerdown="start"
			@pointermove="move"
			@pointerup="stop"
			@pointercancel="stop"
		/><button type="button" class="text-button" @click="clear">Clear signature</button>
	</div>
</template>
