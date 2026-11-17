<script setup>
import { ref } from "vue";
import { api, date } from "../api";
defineProps({ stats: Object });
const days = ref([]),
	error = ref(""),
	loaded = ref(false);
async function expand(event) {
	if (!event.target.open || loaded.value) return;
	try {
		days.value = await api("dashboard.throughput", { days: 30 });
		loaded.value = true;
	} catch (e) {
		error.value = e.message;
	}
}
</script>
<template>
	<details class="activity-summary" @toggle="expand">
		<summary>{{ __("Activity overview") }}</summary>
		<dl>
			<div>
				<dt>{{ __("Total documents") }}</dt>
				<dd>{{ stats.total || 0 }}</dd>
			</div>
			<div>
				<dt>{{ __("Completion rate") }}</dt>
				<dd>{{ stats.completion_rate || 0 }}%</dd>
			</div>
			<div>
				<dt>{{ __("Awaiting me") }}</dt>
				<dd>{{ stats.awaiting_me || 0 }}</dd>
			</div>
			<div>
				<dt>{{ __("Active templates") }}</dt>
				<dd>{{ stats.templates || 0 }}</dd>
			</div>
		</dl>
		<h2>{{ __("Completions in the last 30 days") }}</h2>
		<p v-if="error" role="alert">{{ error }}</p>
		<p v-else-if="!loaded">{{ __("Loading activity…") }}</p>
		<p v-else-if="!days.length">{{ __("No completed documents in this period.") }}</p>
		<table v-else>
			<thead>
				<tr>
					<th>{{ __("Date") }}</th>
					<th>{{ __("Completed documents") }}</th>
				</tr>
			</thead>
			<tbody>
				<tr v-for="day in days" :key="day.day">
					<td>{{ date(day.day) }}</td>
					<td>{{ day.count }}</td>
				</tr>
			</tbody>
		</table>
	</details>
</template>
