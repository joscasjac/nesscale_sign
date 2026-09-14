<script setup>
import { ref, computed, nextTick } from "vue";
import EditorButton from "./EditorButton.vue";
import { activeVariable, variableSuggestions } from "../variables";
const props = defineProps({
	modelValue: String,
	variables: { type: Array, default: () => [] },
	multiline: Boolean,
	label: String,
	placeholder: String,
	maxlength: [Number, String],
});
const emit = defineEmits(["update:modelValue"]);
const control = ref(null),
	open = ref(false),
	caret = ref(0),
	index = ref(0),
	explicit = ref(false);
const query = computed(() =>
	explicit.value ? "" : activeVariable(props.modelValue || "", caret.value)?.query || "",
);
const options = computed(() => variableSuggestions(props.variables, query.value));
function input(e) {
	caret.value = e.target.selectionStart;
	emit("update:modelValue", e.target.value);
	explicit.value = false;
	open.value = !!activeVariable(e.target.value, caret.value);
	index.value = 0;
}
async function insert(option) {
	const value = props.modelValue || "",
		start = explicit.value
			? caret.value
			: (activeVariable(value, caret.value)?.start ?? caret.value),
		token = "{{" + option.key + "}}";
	emit(
		"update:modelValue",
		value.slice(0, start) + token + value.slice(control.value.selectionEnd ?? caret.value),
	);
	open.value = false;
	await nextTick();
	control.value.focus();
	control.value.setSelectionRange(start + token.length, start + token.length);
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
</script>
<template>
	<div class="variable-input">
		<label
			>{{ label
			}}<component
				:is="multiline ? 'textarea' : 'input'"
				ref="control"
				:value="modelValue"
				:aria-label="label"
				:placeholder="placeholder"
				:maxlength="maxlength"
				:rows="multiline ? 5 : undefined"
				@input="input"
				@select="caret = $event.target.selectionStart"
				@keydown="key" /></label
		><EditorButton
			icon="Tag"
			:label="'Insert variable in ' + label"
			@mousedown.prevent
			@click="
				explicit = true;
				open = !open;
				index = 0;
			"
		/>
		<div
			v-if="open"
			class="variable-menu"
			role="listbox"
			:aria-label="'Variables for ' + label"
		>
			<button
				v-for="(o, i) in options"
				role="option"
				:aria-selected="index === i"
				@mousedown.prevent
				@click="insert(o)"
			>
				{{ o.key }}<small>{{ o.value || o.label }}</small>
			</button>
			<p v-if="!options.length">No matching variables</p>
		</div>
	</div>
</template>
