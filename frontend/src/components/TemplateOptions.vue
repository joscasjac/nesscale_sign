<script setup>
defineProps({ form: Object });
</script>
<template>
	<details class="template-options">
		<summary>{{ __("Template rules & ERP automation") }}</summary>
		<label>{{ __("Description") }}<textarea v-model="form.description" rows="2" /></label>
		<label
			>{{ __("Default expiry (days)") }}<input type="number" min="1" v-model.number="form.expiry_days"
		/></label>
		<label>{{ __("Invitation email body") }}<textarea v-model="form.email_message" rows="3" /></label>
		<label class="check-label"
			><input
				type="checkbox"
				v-model="form.auto_create"
				:true-value="1"
				:false-value="0"
			/>{{ __("Create automatically from ERP records") }}</label
		>
		<template v-if="form.auto_create">
			<label
				>{{ __("Reference DocType") }}<input
					v-model="form.trigger_doctype"
					:placeholder="__('For example, Sales Order')"
			/></label>
			<label
				>{{ __("Trigger") }}<select v-model="form.trigger_event">
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
						:value="event"
					>
						{{ __(event) }}
					</option>
				</select></label
			>
			<label v-if="form.trigger_event === 'Value Change'"
				>{{ __("Changed field") }}<input v-model="form.trigger_value_field"
			/></label>
			<label v-if="form.trigger_event === 'Value Change'"
				>{{ __("Target value") }}<input v-model="form.trigger_value_to"
			/></label>
			<template v-if="['Days Before', 'Days After'].includes(form.trigger_event)">
				<label>{{ __("Date field") }}<input v-model="form.trigger_date_field" /></label>
				<label
					>{{ __("Number of days") }}<input type="number" min="0" v-model.number="form.trigger_days"
				/></label>
			</template>
			<label class="check-label"
				><input
					type="checkbox"
					v-model="form.trigger_auto_send"
					:true-value="1"
					:false-value="0"
				/>{{ __("Send automatically when recipients are resolved") }}</label
			>
			<p>
				{{
					__("Recipient mappings below read from this ERP record. Save these rules with the reusable template.")
				}}
			</p>
			<fieldset v-for="(signer, index) in form.signers" :key="signer.role_key">
				<legend>{{ signer.role_label || __("Recipient {0}", [index + 1]) }}</legend>
				<label>{{ __("Role name") }}<input v-model="signer.role_label" /></label>
				<label
					>{{ __("Email field") }}<input
						v-model="signer.source_email_field"
						placeholder="contact_email"
				/></label>
				<label
					>{{ __("Name field") }}<input
						v-model="signer.source_name_field"
						placeholder="customer_name"
				/></label>
				<label
					>{{ __("Fixed email (optional)") }}<input type="email" v-model="signer.manual_email"
				/></label>
				<label>{{ __("Fixed name (optional)") }}<input v-model="signer.manual_name" /></label>
			</fieldset>
		</template>
	</details>
</template>
