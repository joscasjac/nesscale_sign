<script setup>
import { ref, onMounted, watch, computed } from "vue";
import { activeVariable, variableSuggestions, resolveVariables } from "../variables";
const props = defineProps({
	html: String,
	text: String,
	variables: Array,
	label: String,
	preview: Boolean,
});
const emit = defineEmits(["change", "focus"]);
const el = ref(null),
	open = ref(false),
	query = ref(""),
	index = ref(0);
let range = null;
const options = computed(() => variableSuggestions(props.variables || [], query.value));
function escaped(text) {
	const d = document.createElement("div");
	d.textContent = text || "";
	return d.innerHTML.replaceAll("\n", "<br>");
}
function sanitize(html) {
	const t = document.createElement("template");
	t.innerHTML = html;
	for (const e of [...t.content.querySelectorAll("*")]) {
		if (
			![
				"B",
				"STRONG",
				"I",
				"EM",
				"U",
				"S",
				"BR",
				"P",
				"DIV",
				"UL",
				"OL",
				"LI",
				"SPAN",
				"H1",
				"H2",
				"H3",
				"H4",
				"H5",
			].includes(e.tagName)
		) {
			e.replaceWith(...e.childNodes);
			continue;
		}
		for (const a of [...e.attributes]) e.removeAttribute(a.name);
	}
	return t.innerHTML;
}
function sync() {
	if (document.activeElement !== el.value || props.preview) {
		let html = props.html || escaped(props.text);
		if (props.preview)
			html = html.replace(/{{\s*([A-Za-z][A-Za-z0-9_.]*)\s*}}/g, (t) =>
				escaped(resolveVariables(t, props.variables || [])),
			);
		el.value.innerHTML = sanitize(html);
	}
}
onMounted(sync);
watch(() => [props.html, props.text, props.preview, props.variables], sync);
function input() {
	const selection = window.getSelection();
	if (selection.rangeCount) {
		range = selection.getRangeAt(0).cloneRange();
		const before = range.cloneRange();
		before.selectNodeContents(el.value);
		before.setEnd(range.endContainer, range.endOffset);
		const active = activeVariable(before.toString());
		open.value = !!active;
		query.value = active?.query || "";
		index.value = 0;
	}
	emit("change", { html: sanitize(el.value.innerHTML), text: el.value.innerText });
}
function focus() {
	emit("focus", { command, insertMenu });
}
function insertMenu() {
	el.value.focus();
	const s = window.getSelection();
	if (s.rangeCount) range = s.getRangeAt(0).cloneRange();
	open.value = true;
	query.value = "";
}
function insert(o) {
	el.value.focus();
	const s = window.getSelection();
	if (range) {
		s.removeAllRanges();
		s.addRange(range);
		const node = range.startContainer;
		if (node.nodeType === 3) {
			const active = activeVariable(node.textContent, range.startOffset);
			if (active) range.setStart(node, active.start);
		}
	}
	document.execCommand("insertText", false, "{{" + o.key + "}}");
	input();
	open.value = false;
}
function command(name, value = null) {
	el.value.focus();
	if (range) {
		const s = window.getSelection();
		s.removeAllRanges();
		s.addRange(range);
	}
	document.execCommand(name, false, value);
	input();
}
function key(e) {
	if (!open.value) return;
	if (e.key === "Escape") {
		open.value = false;
		e.preventDefault();
	}
	if (["ArrowDown", "ArrowUp"].includes(e.key)) {
		e.preventDefault();
		index.value =
			(index.value + (e.key === "ArrowDown" ? 1 : -1) + options.value.length) %
			options.value.length;
	}
	if (["Enter", "Tab"].includes(e.key) && options.value[index.value]) {
		e.preventDefault();
		insert(options.value[index.value]);
	}
}
function paste(e) {
	document.execCommand("insertText", false, e.clipboardData.getData("text/plain"));
	input();
}
function remember() {
	const s = window.getSelection();
	if (s.rangeCount) range = s.getRangeAt(0).cloneRange();
}
</script>
<template>
	<div class="rich-block-wrap">
		<div
			ref="el"
			class="rich-block"
			:contenteditable="!preview"
			role="textbox"
			aria-multiline="true"
			:aria-label="label"
			spellcheck="true"
			@input="input"
			@focus="focus"
			@keyup="remember"
			@mouseup="remember"
			@keydown="key"
			@paste.prevent="paste"
		></div>
		<div v-if="open" class="variable-menu" role="listbox" aria-label="Document variables">
			<button
				v-for="(o, i) in options"
				role="option"
				:aria-selected="index === i"
				@mousedown.prevent
				@click="insert(o)"
			>
				{{ o.key }}<small>{{ o.value || o.label }}</small>
			</button>
			<p v-if="!options.length">No matching variables. Add one in Document variables.</p>
		</div>
	</div>
</template>
