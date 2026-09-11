<script setup>
import { ref, watch, nextTick } from "vue";
import SignaturePad from "./SignaturePad.vue";
const props = defineProps({
	field: Object,
	value: [String, Number, Boolean],
	signature: Object,
	signerName: String,
	signerEmail: String,
});
const emit = defineEmits(["save", "close"]);
const dialog = ref(null),
	entry = ref(""),
	adopted = ref(null);
const signatureTypes = ["Signature", "Initial", "Stamp"];
watch(
	() => props.field,
	async (field) => {
		if (!field) {
			dialog.value?.close();
			return;
		}
		entry.value =
			props.value ||
			(field.field_type === "Name"
				? props.signerName
				: field.field_type === "Email"
					? props.signerEmail
					: "") ||
			"";
		adopted.value = props.signature;
		await nextTick();
		if (!dialog.value.open) dialog.value.showModal();
		await nextTick();
		(
			dialog.value.querySelector("input:not([type=file]), select") ||
			dialog.value.querySelector("button")
		)?.focus();
	},
);
function save() {
	if (signatureTypes.includes(props.field.field_type) && !adopted.value) return;
	emit("save", { field: props.field, value: entry.value, signature: adopted.value });
}
</script>
<template>
	<dialog
		ref="dialog"
		class="sign-field-dialog"
		aria-labelledby="field-dialog-title"
		@cancel.prevent="$emit('close')"
	>
		<form v-if="field" @submit.prevent="save">
			<div class="dialog-heading">
				<div>
					<p>Page {{ field.page }} · {{ field.required ? "Required" : "Optional" }}</p>
					<h2 id="field-dialog-title">
						{{
							signatureTypes.includes(field.field_type)
								? "Adopt your signature"
								: field.label || field.field_type
						}}
					</h2>
				</div>
				<button
					type="button"
					class="text-button"
					aria-label="Close field editor"
					@click="$emit('close')"
				>
					Close
				</button>
			</div>
			<template v-if="signatureTypes.includes(field.field_type)">
				<p>
					Choose how your signature will appear. It will be applied to your signature,
					initial and stamp fields when you finish signing.
				</p>
				<SignaturePad
					:key="field.field_key"
					:initial-name="signature?.text || signerName"
					@change="adopted = $event"
				/>
			</template>
			<label v-else-if="field.field_type === 'Checkbox'" class="check-label"
				><input
					type="checkbox"
					v-model="entry"
					true-value="1"
					false-value=""
					:required="!!field.required"
				/>{{ field.label }}</label
			>
			<label v-else
				>{{ field.label || field.field_type }}
				<select
					v-if="field.field_type === 'Dropdown'"
					v-model="entry"
					:required="!!field.required"
				>
					<option value="">Choose an option</option>
					<option
						v-for="option in (field.options || '').split('\n').filter(Boolean)"
						:key="option"
					>
						{{ option }}
					</option>
				</select>
				<input
					v-else
					v-model="entry"
					:type="field.field_type === 'Email' ? 'email' : 'text'"
					:required="!!field.required"
					maxlength="10000"
					:autocomplete="
						field.field_type === 'Name'
							? 'name'
							: field.field_type === 'Email'
								? 'email'
								: 'off'
					"
				/>
			</label>
			<div class="dialog-actions">
				<button type="button" @click="$emit('close')">Cancel</button
				><button
					class="primary"
					:disabled="signatureTypes.includes(field.field_type) && !adopted"
				>
					{{
						signatureTypes.includes(field.field_type)
							? "Adopt signature & continue"
							: "Apply & continue"
					}}
				</button>
			</div>
			<small
				>Nothing is submitted until you review the document and choose Finish
				signing.</small
			>
		</form>
	</dialog>
</template>
