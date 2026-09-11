<script setup>
defineProps({ compact: Boolean });
defineEmits(["home"]);
</script>
<template>
	<a
		class="brand identity"
		:class="{ 'identity-compact': compact }"
		href="/nesscale-sign"
		aria-label="Open E-Sign home"
		@click.prevent="$emit('home')"
	>
		<svg class="identity-symbol" viewBox="0 0 40 44" fill="none" aria-hidden="true">
			<path
				d="M9 5h17l7 7v25a3 3 0 0 1-3 3H9a3 3 0 0 1-3-3V8a3 3 0 0 1 3-3Z"
				stroke="currentColor"
				stroke-width="2"
			/>
			<path d="M25 5v9h8" stroke="currentColor" stroke-width="2" stroke-linejoin="round" />
			<path
				d="M11 30c7-9 11-12 10-7-1 4-10 13-10 10 0-2 5-7 8-5 2 2 4-3 5-2 1 2 3 3 6 1"
				stroke="currentColor"
				stroke-width="2.2"
				stroke-linecap="round"
				stroke-linejoin="round"
			/>
		</svg>
		<span class="identity-name">Open E-Sign<small v-if="!compact">for ERPNext</small></span>
	</a>
</template>
