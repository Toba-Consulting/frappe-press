<template>
	<router-link
		:to="{ name: 'Bench Detail', params: { name: bench.name } }"
		class="block border border-gray-300 bg-white p-5 transition hover:border-blue-500"
		:class="{ 'border-blue-500': isActive }"
	>
		<div class="mb-4 flex items-start justify-between">
			<h3 class="text-xl font-semibold text-gray-900">{{ bench.name }}</h3>
			<span
				class="ml-2 inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium"
				:class="statusClass"
			>
				<span class="mr-1 h-1.5 w-1.5 rounded-full" :class="statusDotClass"></span>
				{{ bench.status }}
			</span>
		</div>

		<div class="space-y-3">
			<div class="flex items-center text-base text-gray-600">
				<lucide-monitor class="mr-2 h-4 w-4" />
				<span class="font-medium text-gray-700">Sites</span>
				<span class="ml-auto">{{ bench.site_count || 0 }}</span>
			</div>

			<div class="flex items-center text-base text-gray-600">
				<img v-if="bench.cluster_image" :src="bench.cluster_image" class="mr-2 h-4 w-4" :alt="bench.cluster_title" />
				<lucide-globe v-else class="mr-2 h-4 w-4" />
				<span class="font-medium text-gray-700">Region</span>
				<span class="ml-auto">{{ bench.cluster_title || bench.cluster }}</span>
			</div>

			<div class="flex items-start text-base text-gray-600">
				<lucide-grid-2x2 class="mr-2 mt-0.5 h-4 w-4 shrink-0" />
				<span class="font-medium text-gray-700">Bench Group</span>
				<span class="ml-auto max-w-[200px] truncate text-right" :title="bench.group_title || bench.group">
					{{ bench.group_title || bench.group }}
				</span>
			</div>
		</div>
	</router-link>
</template>

<script setup>
import { computed } from 'vue';

const props = defineProps({
	bench: {
		type: Object,
		required: true,
	},
	isActive: {
		type: Boolean,
		default: false,
	},
});

const statusClass = computed(() => {
	const status = props.bench.status;
	if (status === 'Active') return 'bg-green-50 text-green-700';
	if (status === 'Pending') return 'bg-yellow-50 text-yellow-700';
	if (status === 'Installing') return 'bg-blue-50 text-blue-700';
	if (status === 'Updating') return 'bg-blue-50 text-blue-700';
	if (status === 'Broken') return 'bg-red-50 text-red-700';
	if (status === 'Archived') return 'bg-gray-100 text-gray-600';
	return 'bg-gray-100 text-gray-600';
});

const statusDotClass = computed(() => {
	const status = props.bench.status;
	if (status === 'Active') return 'bg-green-500';
	if (status === 'Pending') return 'bg-yellow-500';
	if (status === 'Installing') return 'bg-blue-500';
	if (status === 'Updating') return 'bg-blue-500';
	if (status === 'Broken') return 'bg-red-500';
	if (status === 'Archived') return 'bg-gray-400';
	return 'bg-gray-400';
});
</script>
