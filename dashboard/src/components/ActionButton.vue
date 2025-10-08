<template>
	<Button v-if="buttonProps" v-bind="buttonProps" class="action-button">
		<template
			v-for="(slot, slotName) in buttonProps.slots"
			v-slot:[slotName]="slotProps"
		>
			<component :is="slot" v-bind="slotProps" />
		</template>
	</Button>
	<Dropdown v-else-if="dropdownProps" v-bind="dropdownProps">
		<Button v-bind="dropdownProps.button" class="action-button-menu" />
	</Dropdown>
</template>
<script>
import { Button, Dropdown } from 'frappe-ui';
import { icon } from '../utils/components';

export default {
	name: 'ActionButton',
	components: {
		Button,
		Dropdown,
	},
	computed: {
		buttonProps() {
			if (!this.$attrs.label || this.$attrs.options) return null;
			return this.$attrs;
		},

		dropdownProps() {
			if (!this.$attrs.options) return null;
			return {
				button: {
					label: '',
					variant: 'outline',
					slots: {
						icon: icon('more-vertical'),
					},
				},
				...this.$attrs,
				options: this.$attrs.options,
			};
		},
	},
};
</script>

<style scoped>
:deep(.action-button) {
	border-radius: 0.5rem;
	padding: 0.625rem 1.25rem;
	font-weight: 500;
	font-size: 0.875rem;
	line-height: 1.25rem;
}

:deep(.action-button-menu) {
	min-width: 2.75rem;
	width: 2.75rem;
	height: 2.75rem;
	padding: 0;
	border-radius: 0.5rem;
	display: flex;
	align-items: center;
	justify-content: center;
}

:deep(.action-button-menu svg) {
	width: 1.25rem;
	height: 1.25rem;
}
</style>
