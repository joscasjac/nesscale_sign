<script setup>
import { ref } from "vue";
import { api } from "../api";
const emit = defineEmits(["select"]);
const query = ref(""),
	results = ref([]),
	error = ref(""),
	busy = ref(false),
	searched = ref(false);
async function search() {
	busy.value = true;
	error.value = "";
	try {
		results.value = await api("contacts.search_contacts", { query: query.value });
		searched.value = true;
	} catch (e) {
		error.value = e.message;
	} finally {
		busy.value = false;
	}
}
async function choose(name) {
	busy.value = true;
	error.value = "";
	try {
		emit("select", await api("contacts.get_contact_prefill", { name }));
		results.value = [];
		searched.value = false;
		query.value = "";
	} catch (e) {
		error.value = e.message;
	} finally {
		busy.value = false;
	}
}
</script>
<template>
	<details class="contact-picker">
		<summary>Fill from a contact</summary>
		<label
			>Contact name<input
				v-model="query"
				placeholder="Search your contacts"
				@keydown.enter.prevent="search"
		/></label>
		<button type="button" :disabled="busy" @click="search">
			{{ busy ? "Loading…" : "Find contact" }}
		</button>
		<p v-if="error" role="alert" class="error">{{ error }}</p>
		<p v-else-if="searched && !results.length" class="muted">
			No matching contacts you can access.
		</p>
		<ul v-if="results.length">
			<li v-for="contact in results" :key="contact.name">
				<button type="button" :disabled="busy" @click="choose(contact.name)">
					{{ contact.full_name || contact.name
					}}<small>{{ contact.email_id || "No email address" }}</small>
				</button>
			</li>
		</ul>
		<small
			>Name and email are copied into this recipient for review. Later contact changes won’t
			change the document.</small
		>
	</details>
</template>
