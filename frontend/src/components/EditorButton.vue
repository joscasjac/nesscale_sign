<script setup>
import { editorIcons as icons } from "../editor-icons";
defineProps({ label: String, icon: String, active: Boolean, badge: String });
</script>
<template>
	<button
		type="button"
		:aria-label="label"
		:data-tooltip="label"
		:class="['editor-icon', { active }]"
	>
		<component :is="icons[icon] || icons.Plus" :size="19" aria-hidden="true" />
		<span
			v-if="badge"
			:class="['editor-icon-badge', { destructive: badge === '×' }]"
			aria-hidden="true"
			>{{ badge }}</span
		>
	</button>
</template>
