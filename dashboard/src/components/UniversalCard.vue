<template>
	<div>
		<!-- Loading State -->
		<div v-if="loading" class="flex justify-center py-8">
			<Spinner class="h-6 w-6 text-gray-600" />
		</div>

		<!-- Render appropriate card component based on gateway -->
		<component
			v-else
			:is="cardComponent"
			:without-address="withoutAddress"
			@complete="handleComplete"
		/>

		<!-- Error Message -->
		<ErrorMessage v-if="errorMessage" :message="errorMessage" class="mt-4" />
	</div>
</template>

<script>
import { Spinner, ErrorMessage } from 'frappe-ui';
import StripeCard from './StripeCard.vue';
import MidtransCard from './MidtransCard.vue';

export default {
	name: 'UniversalCard',
	props: ['withoutAddress'],
	emits: ['complete'],
	components: {
		Spinner,
		ErrorMessage,
		StripeCard,
		MidtransCard,
	},
	data() {
		return {
			loading: true,
			gateway: null,
			cardComponent: null,
			errorMessage: null,
		};
	},
	async mounted() {
		await this.setupCard();
	},
	methods: {
		async setupCard() {
			try {
				// Get the default payment gateway configuration
				const config = await this.$call(
					'press.api.billing.get_default_payment_gateway_config'
				);
				
				this.gateway = config.gateway;
				
				// Set the appropriate component
				if (config.gateway === 'Stripe') {
					this.cardComponent = 'StripeCard';
				} else {
					this.cardComponent = 'MidtransCard';
				}
				
			} catch (error) {
				console.error('Failed to setup payment card:', error);
				this.errorMessage = 'Failed to initialize payment system';
				// Default to Midtrans if configuration fails
				this.cardComponent = 'MidtransCard';
			} finally {
				this.loading = false;
			}
		},
		
		handleComplete(result) {
			this.$emit('complete', {
				...result,
				gateway: this.gateway
			});
		}
	}
};
</script>