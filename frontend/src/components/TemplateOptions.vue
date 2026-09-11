<script setup>
defineProps({ form: Object });
</script>
<template>
	<details class="template-options">
		<summary>Template rules & ERP automation</summary>
		<label>Description<textarea v-model="form.description" rows="2" /></label>
		<label
			>Default expiry (days)<input type="number" min="1" v-model.number="form.expiry_days"
		/></label>
		<label>Invitation email body<textarea v-model="form.email_message" rows="3" /></label>
		<label class="check-label"
			><input
				type="checkbox"
				v-model="form.auto_create"
				:true-value="1"
				:false-value="0"
			/>Create automatically from ERP records</label
		>
		<template v-if="form.auto_create">
			<label
				>Reference DocType<input
					v-model="form.trigger_doctype"
					placeholder="For example, Sales Order"
			/></label>
			<label
				>Trigger<select v-model="form.trigger_event">
					<option
						v-for="event in [
							'New',
							'Save',
							'Submit',
							'Cancel',
							'Value Change',
							'Days Before',
							'Days After',
						]"
					>
						{{ event }}
					</option>
				</select></label
			>
			<label v-if="form.trigger_event === 'Value Change'"
				>Changed field<input v-model="form.trigger_value_field"
			/></label>
			<label v-if="form.trigger_event === 'Value Change'"
				>Target value<input v-model="form.trigger_value_to"
			/></label>
			<template v-if="['Days Before', 'Days After'].includes(form.trigger_event)">
				<label>Date field<input v-model="form.trigger_date_field" /></label>
				<label
					>Number of days<input type="number" min="0" v-model.number="form.trigger_days"
				/></label>
			</template>
			<label class="check-label"
				><input
					type="checkbox"
					v-model="form.trigger_auto_send"
					:true-value="1"
					:false-value="0"
				/>Send automatically when recipients are resolved</label
			>
			<p>
				Recipient mappings below read from this ERP record. Save these rules with the
				reusable template.
			</p>
			<fieldset v-for="(signer, index) in form.signers" :key="signer.role_key">
				<legend>{{ signer.role_label || `Recipient ${index + 1}` }}</legend>
				<label>Role name<input v-model="signer.role_label" /></label>
				<label
					>Email field<input
						v-model="signer.source_email_field"
						placeholder="contact_email"
				/></label>
				<label
					>Name field<input
						v-model="signer.source_name_field"
						placeholder="customer_name"
				/></label>
				<label
					>Fixed email (optional)<input type="email" v-model="signer.manual_email"
				/></label>
				<label>Fixed name (optional)<input v-model="signer.manual_name" /></label>
			</fieldset>
		</template>
	</details>
</template>
