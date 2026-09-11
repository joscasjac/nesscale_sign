<script setup>
import { ref, watch, nextTick } from "vue";
const props = defineProps({
	field: Object,
	value: [String, Number, Boolean],
	active: Boolean,
	complete: Boolean,
});
const emit = defineEmits(["activate", "edit", "save"]);
const input = ref(null);
watch(
	() => props.active,
	async (active) => {
		if (active) {
			await nextTick();
			input.value?.focus();
		}
	},
	{ immediate: true },
);
function save() {
	if (input.value?.reportValidity()) emit("save", props.value);
}
</script>
<template>
	<div
		:class="[
			'placed-field',
			'inline-sign-field',
			{ 'field-active': active, 'field-complete': complete },
		]"
	>
		<span v-if="field.required" class="required-mark" aria-hidden="true">*</span>
		<select
			v-if="field.field_type === 'Dropdown'"
			ref="input"
			:value="value"
			:aria-label="field.label || field.field_type"
			:required="!!field.required"
			@focus="$emit('activate')"
			@change="$emit('edit', $event.target.value)"
			@keydown.enter.prevent="save"
		>
			<option value="">Choose…</option>
			<option
				v-for="option in (field.options || '').split('\n').filter(Boolean)"
				:key="option"
			>
				{{ option }}
			</option>
		</select>
		<input
			v-else
			ref="input"
			:type="
				field.field_type === 'Date'
					? 'date'
					: field.field_type === 'Email'
						? 'email'
						: field.field_type === 'Checkbox'
							? 'checkbox'
							: 'text'
			"
			:value="value"
			:checked="field.field_type === 'Checkbox' ? !!value : undefined"
			:aria-label="field.label || field.field_type"
			:placeholder="field.label || field.field_type"
			:required="!!field.required"
			maxlength="10000"
			@focus="$emit('activate')"
			@input="
				$emit(
					'edit',
					field.field_type === 'Checkbox'
						? $event.target.checked
							? '1'
							: ''
						: $event.target.value,
				)
			"
			@keydown.enter.prevent="save"
		/>
		<button v-if="active" type="button" class="field-next-guide" @click="save">
			Next <span aria-hidden="true">→</span>
		</button>
	</div>
</template>
