<template>
	<div class="space-y-4">
		<!-- Payment Methods Header -->
		<div class="flex items-center justify-between">
			<div>
				<h3 class="text-lg font-semibold text-gray-900">Payment Methods</h3>
				<p class="text-sm text-gray-600">
					Manage your saved payment methods for {{ paymentGatewayLabel }}
				</p>
			</div>
			<Button
				variant="solid"
				@click="showAddCard = true"
				:loading="loading"
			>
				<template #icon>
					<lucide-plus class="h-4 w-4" />
				</template>
				Add Card
			</Button>
		</div>

		<!-- Loading State -->
		<div v-if="loading" class="flex justify-center py-8">
			<Spinner class="h-6 w-6 text-gray-600" />
		</div>

		<!-- Payment Methods List -->
		<div v-else-if="paymentMethods.length > 0" class="space-y-3">
			<PaymentMethodCard
				v-for="method in paymentMethods"
				:key="method.name"
				:payment-method="method"
				:gateway="paymentGateway"
				@deleted="handlePaymentMethodDeleted"
				@default-changed="handleDefaultChanged"
			/>
		</div>

		<!-- Empty State -->
		<div v-else class="text-center py-12">
			<lucide-credit-card class="mx-auto h-12 w-12 text-gray-400" />
			<h3 class="mt-2 text-sm font-medium text-gray-900">No payment methods</h3>
			<p class="mt-1 text-sm text-gray-500">
				Add a payment method to start making payments
			</p>
			<div class="mt-6">
				<Button
					variant="solid"
					@click="showAddCard = true"
				>
					<template #icon>
						<lucide-plus class="h-4 w-4" />
					</template>
					Add your first card
				</Button>
			</div>
		</div>

		<!-- Add Card Dialog -->
		<UniversalCardDialog
			v-model="showAddCard"
			@complete="handleCardAdded"
		/>

		<!-- Error Message -->
		<ErrorMessage v-if="errorMessage" :message="errorMessage" class="mt-4" />
	</div>
</template>

<script>
import { Button, Spinner, ErrorMessage } from 'frappe-ui';
import PaymentMethodCard from './PaymentMethodCard.vue';
import UniversalCardDialog from './UniversalCardDialog.vue';
import { PAYMENT_GATEWAYS } from '../utils/payment';

export default {
	name: 'PaymentMethodsList',
	inject: ['team'],
	components: {
		Button,
		Spinner,
		ErrorMessage,
		PaymentMethodCard,
		UniversalCardDialog,
	},
	data() {
		return {
			paymentMethods: [],
			loading: false,
			showAddCard: false,
			errorMessage: null,
		};
	},
	computed: {
		paymentGatewayLabel() {
			// Will be determined dynamically by the universal components
			return 'Default Payment Gateway';
		}
	},
	async mounted() {
		await this.loadPaymentMethods();
	},
	methods: {
		async loadPaymentMethods() {
			this.loading = true;
			this.errorMessage = null;
			
			try {
				// Use the universal payment methods endpoint
				const response = await this.$call('press.api.billing.get_payment_methods');
				this.paymentMethods = response || [];
			} catch (error) {
				console.error('Failed to load payment methods:', error);
				this.errorMessage = 'Failed to load payment methods';
			} finally {
				this.loading = false;
			}
		},
		
		handleCardAdded(result) {
			console.log('Card added:', result);
			this.loadPaymentMethods(); // Reload the list
			this.$toast.success('Payment method added successfully');
		},
		
		handlePaymentMethodDeleted(paymentMethodId) {
			this.paymentMethods = this.paymentMethods.filter(
				method => method.name !== paymentMethodId
			);
		},
		
		handleDefaultChanged(paymentMethodId) {
			// Update the UI to reflect new default
			this.paymentMethods = this.paymentMethods.map(method => ({
				...method,
				is_default: method.name === paymentMethodId
			}));
		}
	}
};
</script>