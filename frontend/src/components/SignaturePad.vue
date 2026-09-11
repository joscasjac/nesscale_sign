<script setup>
import { ref, onMounted } from "vue";
const emit = defineEmits(["change"]);
const canvas = ref(null),
	mode = ref("Type"),
	name = ref("");
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
onMounted(clear);
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
		</div>
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
