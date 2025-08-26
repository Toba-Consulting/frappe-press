<template>
	<div class="rounded-lg border p-4">
		<div class="flex items-center justify-between">
			<div class="flex items-center space-x-3">
				<!-- Card Brand Icon -->
				<div class="flex h-8 w-12 items-center justify-center rounded bg-gray-100">
					<component 
						:is="cardBrandIcon" 
						class="h-4 w-4"
						v-if="cardBrandIcon"
					/>
					<span v-else class="text-xs font-medium text-gray-600">
						{{ (paymentMethod.brand || '').toUpperCase() }}
					</span>
				</div>
				
				<!-- Card Details -->
				<div>
					<div class="flex items-center space-x-2">
						<span class="text-sm font-medium text-gray-900">
							•••• •••• •••• {{ paymentMethod.last_4 || '****' }}
						</span>
						<span 
							v-if="paymentMethod.is_default" 
							class="rounded-full bg-green-100 px-2 py-1 text-xs text-green-800"
						>
							Default
						</span>
					</div>
					<div class="text-xs text-gray-500">
						{{ paymentMethod.name_on_card }}
						<span v-if="paymentMethod.expiry_month && paymentMethod.expiry_year">
							• Expires {{ paymentMethod.expiry_month }}/{{ paymentMethod.expiry_year }}
						</span>
					</div>
					<div class="text-xs text-gray-400">
						{{ paymentGatewayLabel }}
					</div>
				</div>
			</div>
			
			<!-- Actions -->
			<div class="flex items-center space-x-2">
				<Button
					v-if="!paymentMethod.is_default"
					size="sm"
					variant="ghost"
					@click="setAsDefault"
					:loading="settingDefault"
				>
					Set Default
				</Button>
				<Button
					size="sm"
					variant="ghost"
					theme="red"
					@click="deletePaymentMethod"
					:loading="deleting"
				>
					<template #icon>
						<lucide-trash-2 class="h-4 w-4" />
					</template>
				</Button>
			</div>
		</div>
	</div>
</template>

<script>
import { Button } from 'frappe-ui';

export default {
	name: 'PaymentMethodCard',
	props: {
		paymentMethod: {
			type: Object,
			required: true
		}
	},
	emits: ['deleted', 'defaultChanged'],
	components: {
		Button
	},
	data() {
		return {
			settingDefault: false,
			deleting: false,
			gateway: null
		};
	},
	async mounted() {
		// Detect gateway from the payment method or get default
		await this.detectGateway();
	},
	computed: {
		paymentGatewayLabel() {
			return this.gateway === 'Stripe' ? 'Stripe' : 'Midtrans';
		},
		cardBrandIcon() {
			const brand = (this.paymentMethod.brand || '').toLowerCase();
			const icons = {
				'visa': 'lucide-credit-card',
				'mastercard': 'lucide-credit-card',
				'amex': 'lucide-credit-card',
				'discover': 'lucide-credit-card',
			};
			return icons[brand];
		}
	},
	methods: {
		async detectGateway() {
			try {
				// Check if this is a Stripe payment method (has doctype in name)
				if (this.paymentMethod.name && this.paymentMethod.name.startsWith('PM')) {
					this.gateway = 'Stripe';
				} else if (this.paymentMethod.name && this.paymentMethod.name.startsWith('MPM')) {
					this.gateway = 'Midtrans';
				} else {
					// Fallback: get default gateway
					const config = await this.$call('press.api.billing.get_default_payment_gateway_config');
					this.gateway = config.gateway;
				}
			} catch (error) {
				// Default to Midtrans if detection fails
				this.gateway = 'Midtrans';
			}
		},
		
		async setAsDefault() {
			this.settingDefault = true;
			
			try {
				let response;
				if (this.gateway === 'Stripe') {
					// Call Stripe API to set default
					response = await this.$call(
						'press.api.billing.set_default_stripe_payment_method',
						{ payment_method_id: this.paymentMethod.name }
					);
				} else {
					// Call Midtrans API to set default
					response = await this.$call(
						'press.api.billing.set_default_midtrans_payment_method',
						{ payment_method_id: this.paymentMethod.name }
					);
				}
				
				if (response.success) {
					this.$emit('defaultChanged', this.paymentMethod.name);
					this.$toast.success('Default payment method updated');
				} else {
					throw new Error(response.error?.[0] || 'Failed to update default payment method');
				}
			} catch (error) {
				console.error('Failed to set default payment method:', error);
				this.$toast.error(error.message || 'Failed to update payment method');
			} finally {
				this.settingDefault = false;
			}
		},
		
		async deletePaymentMethod() {
			if (!confirm('Are you sure you want to delete this payment method?')) {
				return;
			}
			
			this.deleting = true;
			
			try {
				let response;
				if (this.gateway === 'Stripe') {
					// Call Stripe API to delete
					response = await this.$call(
						'press.api.billing.delete_stripe_payment_method',
						{ payment_method_id: this.paymentMethod.name }
					);
				} else {
					// Call Midtrans API to delete
					response = await this.$call(
						'press.api.billing.delete_midtrans_payment_method',
						{ payment_method_id: this.paymentMethod.name }
					);
				}
				
				if (response.success || response === 'Payment method deleted successfully') {
					this.$emit('deleted', this.paymentMethod.name);
					this.$toast.success('Payment method deleted');
				} else {
					throw new Error(response.error?.[0] || 'Failed to delete payment method');
				}
			} catch (error) {
				console.error('Failed to delete payment method:', error);
				this.$toast.error(error.message || 'Failed to delete payment method');
			} finally {
				this.deleting = false;
			}
		}
	}
};
</script>