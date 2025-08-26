<template>
	<Dialog v-model="show" :options="{ title: 'Add new card with Midtrans' }">
		<template #body-content>
			<p class="text-sm mb-5 text-gray-700" v-if="message">
				{{ message }}
			</p>
			<MidtransCard @complete="handleCardComplete" />
		</template>
	</Dialog>
</template>

<script>
import MidtransCard from './MidtransCard.vue';

export default {
	name: 'MidtransCardDialog',
	props: ['modelValue', 'message'],
	emits: ['update:modelValue', 'complete'],
	components: {
		MidtransCard,
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
	},
	methods: {
		handleCardComplete(result) {
			this.show = false;
			this.$emit('complete', result);
		},
	},
};
</script>