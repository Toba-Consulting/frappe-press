<template>
	<div>
		<div v-if="step == 'Setting up Midtrans'" class="mt-8 flex justify-center">
			<Spinner class="h-4 w-4 text-gray-700" />
		</div>
		<ErrorMessage
			class="mt-2"
			:message="createPaymentIntent.error || errorMessage"
		/>
		<div class="mt-8">
			<Button
				v-if="step == 'Get Amount'"
				class="w-full"
				size="md"
				variant="solid"
				label="Proceed to payment using Midtrans"
				:loading="createPaymentIntent.loading"
				@click="createPaymentIntent.submit()"
			/>
			<Button
				v-else-if="step == 'Processing Payment'"
				class="w-full"
				size="md"
				variant="solid"
				label="Processing Payment..."
				:loading="true"
			/>
		</div>
	</div>
</template>

<script setup>
import { Button, ErrorMessage, Spinner, createResource } from 'frappe-ui';
import { ref, nextTick, inject } from 'vue';
import { toast } from 'vue-sonner';
import { DashboardError } from '../../utils/error';

const props = defineProps({
	amount: {
		type: Number,
		default: 0,
	},
	minimumAmount: {
		type: Number,
		default: 0,
	},
});

const emit = defineEmits(['success']);

const team = inject('team');

const step = ref('Get Amount');
const errorMessage = ref(null);
const snap = ref(null);
const midtransConfig = ref(null);

// Setup Midtrans when component mounts
const setupMidtrans = async () => {
	try {
		step.value = 'Setting up Midtrans';
		
		const result = await $call(
			'press.api.billing.get_midtrans_client_key_and_config'
		);
		
		midtransConfig.value = result;
		
		if (!result.client_key) {
			throw new Error('Midtrans client key not configured');
		}

		await loadMidtransSnap(result.client_key, result.is_sandbox);
		step.value = 'Get Amount';
		
	} catch (error) {
		console.error('Failed to setup Midtrans:', error);
		errorMessage.value = 'Failed to initialize payment system';
		step.value = 'Get Amount';
	}
};

const loadMidtransSnap = (clientKey, isSandbox) => {
	return new Promise((resolve, reject) => {
		const snapUrl = isSandbox 
			? 'https://app.sandbox.midtrans.com/snap/snap.js'
			: 'https://app.midtrans.com/snap/snap.js';

		// Check if script already loaded
		if (window.snap) {
			snap.value = window.snap;
			resolve();
			return;
		}

		const script = document.createElement('script');
		script.src = snapUrl;
		script.setAttribute('data-client-key', clientKey);
		script.onload = () => {
			snap.value = window.snap;
			resolve();
		};
		script.onerror = () => {
			reject(new Error('Failed to load Midtrans Snap'));
		};
		document.head.appendChild(script);
	});
};

const createPaymentIntent = createResource({
	url: 'press.api.billing.create_midtrans_prepaid_credits',
	params() {
		return {
			amount: props.amount,
			currency: team.doc.currency === 'IDR' ? 'IDR' : 'USD',
		};
	},
	onSuccess(response) {
		if (!response.success) {
			errorMessage.value = response.error?.[0] || 'Payment creation failed';
			return;
		}

		step.value = 'Processing Payment';
		
		// Launch Midtrans Snap payment
		snap.value.pay(response.snap_token, {
			onSuccess: (result) => {
				handlePaymentSuccess(result, response.order_id);
			},
			onPending: (result) => {
				handlePaymentPending(result, response.order_id);
			},
			onError: (result) => {
				handlePaymentError(result);
			},
			onClose: () => {
				step.value = 'Get Amount';
			}
		});
	},
	onError(error) {
		console.error('Payment intent creation failed:', error);
		errorMessage.value = error.message || 'Payment creation failed';
		step.value = 'Get Amount';
	}
});

const handlePaymentSuccess = async (result, orderId) => {
	try {
		// Verify payment status
		const verifyResponse = await $call(
			'press.api.billing.verify_midtrans_payment_status',
			{
				order_id: orderId,
				transaction_id: result.transaction_id
			}
		);

		if (verifyResponse.success && verifyResponse.status === 'capture') {
			toast.success('Payment successful! Credits added to your account.');
			emit('success', {
				amount: props.amount,
				transaction_id: result.transaction_id,
				order_id: orderId
			});
		} else {
			throw new Error('Payment verification failed');
		}
	} catch (error) {
		console.error('Payment verification failed:', error);
		errorMessage.value = 'Payment completed but verification failed. Please contact support.';
	} finally {
		step.value = 'Get Amount';
	}
};

const handlePaymentPending = async (result, orderId) => {
	console.log('Payment pending:', result);
	toast.info('Payment is pending. We will update your credits once payment is confirmed.');
	
	// Still emit success as the payment is initiated
	emit('success', {
		amount: props.amount,
		transaction_id: result.transaction_id,
		order_id: orderId,
		status: 'pending'
	});
	
	step.value = 'Get Amount';
};

const handlePaymentError = (result) => {
	console.error('Payment error:', result);
	errorMessage.value = result.status_message || 'Payment failed. Please try again.';
	step.value = 'Get Amount';
};

// Initialize Midtrans when component mounts
setupMidtrans();
</script>