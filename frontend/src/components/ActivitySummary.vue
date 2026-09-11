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
		<summary>Activity overview</summary>
		<dl>
			<div>
				<dt>Total documents</dt>
				<dd>{{ stats.total || 0 }}</dd>
			</div>
			<div>
				<dt>Completion rate</dt>
				<dd>{{ stats.completion_rate || 0 }}%</dd>
			</div>
			<div>
				<dt>Awaiting me</dt>
				<dd>{{ stats.awaiting_me || 0 }}</dd>
			</div>
			<div>
				<dt>Active templates</dt>
				<dd>{{ stats.templates || 0 }}</dd>
			</div>
		</dl>
		<h2>Completions in the last 30 days</h2>
		<p v-if="error" role="alert">{{ error }}</p>
		<p v-else-if="!loaded">Loading activity…</p>
		<p v-else-if="!days.length">No completed documents in this period.</p>
		<table v-else>
			<thead>
				<tr>
					<th>Date</th>
					<th>Completed documents</th>
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
