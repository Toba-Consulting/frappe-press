<template>
	<header
		class="border-b bg-white px-5 py-4 sm:px-5"
		:class="{ 'sticky top-0 z-10': sticky }"
	>
		<div class="flex items-center justify-between">
			<slot />
		</div>
	</header>
</template>

<script setup>
defineProps({
	sticky: {
		type: Boolean,
		default: false,
	},
});
</script>
