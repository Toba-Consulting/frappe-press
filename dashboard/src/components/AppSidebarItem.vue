<template>
	<router-link custom v-slot="{ href, navigate }" :to="item.route">
		<a
			:href="href"
			@click="navigate"
			class="flex items-center rounded px-2 py-1 text-gray-800 transition relative"
			:class="[
				item.isActive ? 'bg-gray-100' : 'hover:bg-gray-50',
				item.disabled ? 'pointer-events-none opacity-50' : '',
				$attrs.class,
			]"
		>
			<div
				v-if="item.isActive && item.name"
				class="absolute left-0 top-0 bottom-0 w-1 rounded-l"
				:style="{ backgroundColor: item.color || '#9C27B0' }"
			></div>
			<div class="flex w-full items-center space-x-2">
				<span class="grid h-5 w-6 place-items-center">
					<component :is="item.icon" class="h-4 w-4 text-gray-500" />
				</span>
				<span class="text-sm font-medium">{{ item.name }}</span>
				<component :is="item.badge" />
			</div>
		</a>
	</router-link>
</template>

<script setup>
let props = defineProps({
	item: {
		type: Object,
		required: true,
	},
});
</script>
