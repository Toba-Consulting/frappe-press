<template>
	<Dialog v-model="show" :options="{ title: dialogTitle }">
		<template #body-content>
			<p class="text-sm mb-5 text-gray-700" v-if="message">
				{{ message }}
			</p>
			<UniversalCard @complete="handleCardComplete" />
		</template>
	</Dialog>
</template>

<script>
import UniversalCard from './UniversalCard.vue';

export default {
	name: 'UniversalCardDialog',
	props: ['modelValue', 'message'],
	emits: ['update:modelValue', 'complete'],
	components: {
		UniversalCard,
	},
	data() {
		return {
			_show: true,
		};
	},
	computed: {
		show: {
			get() {
				return this.modelValue == null ? this._show : this.modelValue;
			},
			set(value) {
				if (this.modelValue == null) {
					this._show = value;
					return;
				}
				this.$emit('update:modelValue', value);
			},
		},
		dialogTitle() {
			return 'Add new payment method';
		}
	},
	methods: {
		handleCardComplete(result) {
			this.show = false;
			this.$emit('complete', result);
		},
	},
};
</script>