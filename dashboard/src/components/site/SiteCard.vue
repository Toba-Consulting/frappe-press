<template>
	<router-link
		:to="{ name: 'Site Detail', params: { name: site.name } }"
		class="block border border-gray-300 bg-white p-5 transition hover:border-green-500"
		:class="{ 'border-green-500': isActive }"
	>
		<div class="mb-4 flex items-start justify-between">
			<h3 class="text-xl font-semibold text-gray-900">{{ site.host_name || site.name }}</h3>
			<span
				class="ml-2 inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium"
				:class="statusClass"
			>
				<span class="mr-1 h-1.5 w-1.5 rounded-full" :class="statusDotClass"></span>
				{{ site.status }}
			</span>
		</div>

		<div class="space-y-3">
			<div class="flex items-center text-base text-gray-600">
				<lucide-radio class="mr-2 h-4 w-4" />
				<span class="font-medium text-gray-700">Plan</span>
				<span class="ml-auto">{{ planText }}</span>
			</div>

			<div class="flex items-center text-base text-gray-600">
				<img v-if="site.cluster_image" :src="site.cluster_image" class="mr-2 h-4 w-4" :alt="site.cluster_title" />
				<lucide-globe v-else class="mr-2 h-4 w-4" />
				<span class="font-medium text-gray-700">Region</span>
				<span class="ml-auto">{{ site.cluster_title || site.cluster }}</span>
			</div>

			<div class="flex items-start text-base text-gray-600">
				<lucide-grid-2x2 class="mr-2 mt-0.5 h-4 w-4 shrink-0" />
				<span class="font-medium text-gray-700">Bench Group</span>
				<span class="ml-auto max-w-[200px] truncate text-right" :title="benchGroupText">
					{{ benchGroupText }}
				</span>
			</div>

			<div class="flex items-center text-base text-gray-600">
				<lucide-radio class="mr-2 h-4 w-4" />
				<span class="font-medium text-gray-700">Version</span>
				<span class="ml-auto">{{ site.version }}</span>
			</div>
		</div>
	</router-link>
</template>

<script setup>
import { computed } from 'vue';
import { getTeam } from '../../data/team';
import { userCurrency } from '../../utils/format';
import { trialDays } from '../../utils/site';

const props = defineProps({
	site: {
		type: Object,
		required: true,
	},
	isActive: {
		type: Boolean,
		default: false,
	},
});

const statusClass = computed(() => {
	const status = props.site.status;
	if (status === 'Active') return 'bg-green-50 text-green-700';
	if (status === 'Inactive') return 'bg-gray-100 text-gray-600';
	if (status === 'Suspended') return 'bg-yellow-50 text-yellow-700';
	if (status === 'Broken') return 'bg-red-50 text-red-700';
	if (status === 'Archived') return 'bg-gray-100 text-gray-600';
	return 'bg-gray-100 text-gray-600';
});

const statusDotClass = computed(() => {
	const status = props.site.status;
	if (status === 'Active') return 'bg-green-500';
	if (status === 'Inactive') return 'bg-gray-400';
	if (status === 'Suspended') return 'bg-yellow-500';
	if (status === 'Broken') return 'bg-red-500';
	if (status === 'Archived') return 'bg-gray-400';
	return 'bg-gray-400';
});

const planText = computed(() => {
	if (props.site.trial_end_date) {
		return trialDays(props.site.trial_end_date);
	}
	const $team = getTeam();
	if (props.site.price_usd > 0) {
		const indonesia = $team.doc?.currency === 'IDR';
		const formattedValue = userCurrency(
			indonesia ? props.site.price_idr : props.site.price_usd,
			0,
		);
		return `${formattedValue}/mo`;
	}
	return props.site.plan_title;
});

const benchGroupText = computed(() => {
	return props.site.group_public ? 'Shared' : props.site.group_title || props.site.group;
});
</script>
