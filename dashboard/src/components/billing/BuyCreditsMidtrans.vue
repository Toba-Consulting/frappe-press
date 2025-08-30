<template>
	<div>
		<ErrorMessage
			class="mt-2"
			:message="errorMessage"
		/>
		<div class="mt-8">
			<Button
				v-if="step == 'Get Amount'"
				class="w-full"
				size="md"
				variant="solid"
				label="Proceed to payment"
				@click="openPaymentMethodDialog"
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

		<!-- Payment Method Selection Dialog -->
		<MidtransPaymentMethodDialog
			v-model="showPaymentMethodDialog"
			:amount="amount"
			@methodSelected="onPaymentMethodSelected"
		/>

		<!-- Bank Selection Dialog -->
		<MidtransBankSelectionDialog
			v-model="showBankSelectionDialog"
			:amount="amount"
			@bankSelected="onBankSelected"
			@goBack="goBackToPaymentMethods"
		/>

		<!-- E-Wallet Selection Dialog -->
		<MidtransEWalletSelectionDialog
			v-model="showEWalletSelectionDialog"
			:amount="amount"
			@walletSelected="onEWalletSelected"
			@goBack="goBackToPaymentMethods"
		/>

		<!-- Payment Instructions Dialog (Bank Transfer) -->
		<MidtransPaymentInstructionsDialog
			v-model="showPaymentInstructionsDialog"
			:paymentData="currentPaymentData"
			@paymentCompleted="onPaymentCompleted"
		/>

		<!-- E-Wallet Instructions Dialog -->
		<MidtransEWalletInstructionsDialog
			v-model="showEWalletInstructionsDialog"
			:paymentData="currentPaymentData"
			@paymentCompleted="onPaymentCompleted"
		/>
	</div>
</template>

<script setup>
import { Button, ErrorMessage, call } from 'frappe-ui';
import { ref, inject, watch } from 'vue';
import { toast } from 'vue-sonner';
import MidtransPaymentMethodDialog from './MidtransPaymentMethodDialog.vue';
import MidtransBankSelectionDialog from './MidtransBankSelectionDialog.vue';
import MidtransEWalletSelectionDialog from './MidtransEWalletSelectionDialog.vue';
import MidtransPaymentInstructionsDialog from './MidtransPaymentInstructionsDialog.vue';
import MidtransEWalletInstructionsDialog from './MidtransEWalletInstructionsDialog.vue';

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

const emit = defineEmits(['success', 'cancel']);

const team = inject('team');

const step = ref('Get Amount');
const errorMessage = ref(null);
const showPaymentMethodDialog = ref(false);
const showBankSelectionDialog = ref(false);
const showEWalletSelectionDialog = ref(false);
const showPaymentInstructionsDialog = ref(false);
const showEWalletInstructionsDialog = ref(false);
const currentPaymentData = ref(null);
const selectedPaymentMethod = ref(null);

// Note: Using direct $call instead of createResource for better error handling

const openPaymentMethodDialog = () => {
	errorMessage.value = null;
	showPaymentMethodDialog.value = true;
};

const onPaymentMethodSelected = ({ method, amount }) => {
	selectedPaymentMethod.value = method;
	
	if (method === 'bank_transfer') {
		showBankSelectionDialog.value = true;
	} else if (method === 'ewallet') {
		showEWalletSelectionDialog.value = true;
	}
};

const onBankSelected = async ({ bank, amount }) => {
	step.value = 'Processing Payment';
	errorMessage.value = null;
	
	try {
		// Call the API method directly since createResource has its own error handling
		const response = await call('press.api.billing.create_midtrans_bank_transfer', {
			amount: amount,
			currency: team.doc.currency || 'USD',
			bank: bank,
			payment_method: 'bank_transfer'
		});
		
		console.log(response)

		if (response.success) {
			currentPaymentData.value = response.data;
			showPaymentInstructionsDialog.value = true;
			step.value = 'Get Amount';
		} else {
			errorMessage.value = response.error || 'Payment creation failed';
			step.value = 'Get Amount';
		}
	} catch (error) {
		console.error('Failed to create bank transfer payment:', error);
		errorMessage.value = error.message || 'Failed to create payment. Please try again.';
		step.value = 'Get Amount';
	}
};

const onEWalletSelected = async ({ wallet, amount }) => {
	step.value = 'Processing Payment';
	errorMessage.value = null;
	
	try {
		const response = await call('press.api.billing.create_midtrans_ewallet_payment', {
			amount: amount,
			currency: team.doc.currency || 'USD',
			ewallet: wallet
		});
		
		console.log('E-Wallet response:', response);

		if (response.success) {
			currentPaymentData.value = response.data;
			showEWalletInstructionsDialog.value = true;
			step.value = 'Get Amount';
		} else {
			errorMessage.value = response.error || 'E-Wallet payment creation failed';
			step.value = 'Get Amount';
		}
	} catch (error) {
		console.error('Failed to create E-Wallet payment:', error);
		errorMessage.value = error.message || 'Failed to create payment. Please try again.';
		step.value = 'Get Amount';
	}
};

const goBackToPaymentMethods = () => {
	showBankSelectionDialog.value = false;
	showEWalletSelectionDialog.value = false;
	showPaymentMethodDialog.value = true;
};

const onPaymentCompleted = (paymentResult) => {
	toast.success('Payment completed successfully! Credits have been added to your account.');
	emit('success', {
		amount: props.amount,
		transaction_id: paymentResult.transaction_id,
		status: paymentResult.status
	});
};

// Cleanup function
const cleanup = () => {
	step.value = 'Get Amount';
	errorMessage.value = null;
	showPaymentMethodDialog.value = false;
	showBankSelectionDialog.value = false;
	showEWalletSelectionDialog.value = false;
	showPaymentInstructionsDialog.value = false;
	showEWalletInstructionsDialog.value = false;
	currentPaymentData.value = null;
	selectedPaymentMethod.value = null;
};

// Handle cancel event
const handleCancel = () => {
	cleanup();
	emit('cancel');
};

// Watch for dialog closures to handle cancellation
watch([showPaymentMethodDialog, showBankSelectionDialog, showEWalletSelectionDialog, showPaymentInstructionsDialog, showEWalletInstructionsDialog], ([method, bank, ewallet, instructions, ewalletInstructions]) => {
	if (!method && !bank && !ewallet && !instructions && !ewalletInstructions && step.value !== 'Processing Payment') {
		// All dialogs closed and not processing - this means user cancelled
		handleCancel();
	}
});
</script>