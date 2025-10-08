<template>
	<router-link
		:to="{ name: 'Release Group Detail', params: { name: group.name } }"
		class="block border border-gray-300 bg-white p-5 transition hover:border-purple-500"
		:class="{ 'border-purple-500': isActive }"
	>
		<div class="mb-4 flex items-start justify-between">
			<h3 class="text-xl font-semibold text-gray-900">{{ group.title }}</h3>
			<span
				class="ml-2 inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium"
				:class="statusClass"
			>
				<span class="mr-1 h-1.5 w-1.5 rounded-full" :class="statusDotClass"></span>
				{{ statusText }}
			</span>
		</div>

		<div class="space-y-3">
			<div class="flex items-center text-base text-gray-600">
				<lucide-radio class="mr-2 h-4 w-4" />
				<span class="font-medium text-gray-700">Version</span>
				<span class="ml-auto">{{ group.version }}</span>
			</div>

			<div class="flex items-start text-base text-gray-600">
				<lucide-grid-2x2 class="mr-2 mt-0.5 h-4 w-4 shrink-0" />
				<span class="font-medium text-gray-700">Apps</span>
				<span class="ml-auto max-w-[200px] truncate text-right" :title="appsText">
					{{ appsText }}
				</span>
			</div>

			<div class="flex items-center text-base text-gray-600">
				<lucide-globe class="mr-2 h-4 w-4" />
				<span class="font-medium text-gray-700">Sites</span>
				<span class="ml-auto">{{ group.site_count || 0 }}</span>
			</div>
		</div>
	</router-link>
</template>

<script setup>
import { computed } from 'vue';

const props = defineProps({
	group: {
		type: Object,
		required: true,
	},
	isActive: {
		type: Boolean,
		default: false,
	},
});

const statusText = computed(() => {
	return props.group.active_benches ? 'Active' : 'Awaiting Deploy';
});

const statusClass = computed(() => {
	return props.group.active_benches
		? 'bg-green-50 text-green-700'
		: 'bg-gray-100 text-gray-600';
});

const statusDotClass = computed(() => {
	return props.group.active_benches ? 'bg-green-500' : 'bg-gray-400';
});

const appsText = computed(() => {
	if (!props.group.apps || props.group.apps.length === 0) {
		return 'No apps';
	}
	return props.group.apps.map((d) => d.app).join(', ');
});
</script>
