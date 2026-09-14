<script setup>
import { ref, watch, nextTick } from "vue";
const props = defineProps({
	open: Boolean,
	consent: Boolean,
	consentText: String,
	busy: Boolean,
	error: String,
});
const emit = defineEmits(["close", "update:consent", "submit"]);
const dialog = ref(null);
watch(
	() => props.open,
	async (open) => {
		await nextTick();
		if (open && !dialog.value.open) dialog.value.showModal();
		else if (!open) dialog.value.close();
	},
);
</script>
<template>
	<dialog
		ref="dialog"
		class="sign-field-dialog final-signing-dialog"
		aria-labelledby="final-signing-title"
		@cancel.prevent="!busy && emit('close')"
	>
		<form @submit.prevent="consent && !busy && emit('submit')">
			<div class="dialog-heading">
				<h2 id="final-signing-title">Ready to finish</h2>
				<button
					type="button"
					aria-label="Back to document"
					:disabled="busy"
					@click="emit('close')"
				>
					×
				</button>
			</div>
			<p>All required fields are complete. Confirm your consent to finish signing.</p>
			<label class="check-label consent"
				><input
					id="finish-signing-consent"
					type="checkbox"
					:checked="consent"
					:disabled="busy"
					required
					@change="emit('update:consent', $event.target.checked)"
				/><span>{{ consentText }}</span></label
			>
			<p v-if="error" class="error" role="alert">{{ error }}</p>
			<footer class="button-group">
				<button type="button" :disabled="busy" @click="emit('close')">
					Review document</button
				><button type="submit" class="primary" :disabled="busy || !consent">
					{{ busy ? "Saving signature…" : "Finish signing" }}
				</button>
			</footer>
		</form>
	</dialog>
</template>
