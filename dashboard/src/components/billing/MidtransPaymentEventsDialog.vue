<template>
	<Dialog
		:modelValue="modelValue"
		@update:modelValue="$emit('update:modelValue', $event)"
	>
		<template #body>
			<div class="px-4 pb-4 pt-5 sm:px-6 sm:pb-4">
				<div class="flex flex-col space-y-4">
					<div class="flex items-center justify-between">
						<h3 class="text-lg font-medium leading-6 text-gray-900">
							Payment History
						</h3>
						<div class="flex gap-2">
							<Button
								:variant="filterStatus === 'all' ? 'solid' : 'outline'"
								size="sm"
								@click="filterStatus = 'all'"
							>
								All
							</Button>
							<Button
								:variant="filterStatus === 'Paid' ? 'solid' : 'outline'"
								size="sm"
								@click="filterStatus = 'Paid'"
							>
								Paid
							</Button>
							<Button
								:variant="filterStatus === 'Pending' ? 'solid' : 'outline'"
								size="sm"
								@click="filterStatus = 'Pending'"
							>
								Pending
							</Button>
						</div>
					</div>
					
					<div class="max-h-96 overflow-y-auto">
						<div v-if="paymentEvents.loading" class="text-center py-8">
							<LoadingIndicator />
						</div>
						
						<div v-else-if="filteredEvents.length === 0" class="text-center py-8 text-gray-500">
							No payment events found
						</div>
						
						<div v-else class="space-y-3">
							<div
								v-for="event in filteredEvents"
								:key="event.name"
								:class="[
									'flex items-center justify-between border rounded-lg p-4',
									getEventBackgroundClass(event.payment_status)
								]"
							>
								<div class="flex-1">
									<div class="flex items-center gap-2 mb-2">
										<span class="font-medium text-gray-900">
											{{ event.invoice }}
										</span>
										<Badge
											:variant="getBadgeVariant(event.payment_status)"
											size="sm"
										>
											{{ event.payment_status }}
										</Badge>
									</div>
									<div class="text-sm text-gray-600 space-y-1">
										<div>
											<span class="font-medium">Type:</span>
											{{ event.payment_type || 'N/A' }}
										</div>
										<div>
											<span class="font-medium">Status:</span>
											{{ event.transaction_status }}
										</div>
									</div>
								</div>
								<div class="text-right flex flex-col items-end gap-2">
									<div class="text-lg font-semibold text-gray-900">
										{{ formatAmount(event) }}
									</div>
									<div class="text-sm text-gray-500">
										{{ formatDate(event.creation) }}
									</div>
									<div class="flex gap-1">
										<Button
											v-if="event.payment_status === 'Paid' && event.invoice"
											size="sm"
											variant="ghost"
											@click="printInvoice(event.invoice)"
										>
											<FeatherIcon class="h-4 w-4" name="printer" />
										</Button>
										<Button
											v-if="event.payment_status === 'Pending'"
											size="sm"
											variant="ghost"
											@click="showPaymentInstructions(event)"
										>
											<FeatherIcon class="h-4 w-4" name="info" />
										</Button>
									</div>
								</div>
							</div>
						</div>
					</div>
				</div>
			</div>
		</template>
		<template #actions>
			<Button variant="ghost" @click="$emit('update:modelValue', false)">
				Close
			</Button>
		</template>
	</Dialog>
	
	<MidtransPaymentInstructionsDialog
		v-if="showPaymentInstructionsDialog"
		v-model="showPaymentInstructionsDialog"
		:paymentData="selectedPaymentData"
		@paymentCompleted="handlePaymentCompleted"
	/>
</template>

<script setup>
import { ref, computed, inject } from 'vue';
import { Dialog, Button, Badge, LoadingIndicator, FeatherIcon, createResource } from 'frappe-ui';
import MidtransPaymentInstructionsDialog from './MidtransPaymentInstructionsDialog.vue';

defineProps(['modelValue']);
defineEmits(['update:modelValue']);

const team = inject('team');
const filterStatus = ref('all');
const showPaymentInstructionsDialog = ref(false);
const selectedPaymentData = ref(null);

const paymentEvents = createResource({
	url: 'frappe.client.get_list',
	params: {
		doctype: 'Midtrans Payment Event',
		fields: [
			'name',
			'midtrans_transaction_id',
			'midtrans_order_id',
			'transaction_status',
			'payment_status',
			'payment_type',
			'invoice',
			'midtrans_transaction_object',
			'creation'
		],
		filters: {
			team: team.doc.name
		},
		order_by: 'creation desc',
		limit: 50
	},
	auto: true
});

const filteredEvents = computed(() => {
	if (!paymentEvents.data) return [];
	
	if (filterStatus.value === 'all') {
		// Show all paid transactions + only the latest pending transaction
		const paidEvents = paymentEvents.data.filter(event => event.payment_status === 'Paid');
		const pendingEvents = paymentEvents.data.filter(event => event.payment_status === 'Pending');
		const latestPending = pendingEvents.length > 0 ? [pendingEvents[0]] : [];
		
		return [...latestPending, ...paidEvents];
	}
	
	if (filterStatus.value === 'Pending') {
		// Show only the latest pending transaction
		const pendingEvents = paymentEvents.data.filter(event => event.payment_status === 'Pending');
		return pendingEvents.length > 0 ? [pendingEvents[0]] : [];
	}
	
	return paymentEvents.data.filter(event => event.payment_status === filterStatus.value);
});

function getBadgeVariant(status) {
	switch (status) {
		case 'Paid':
			return 'green';
		case 'Pending':
			return 'orange';
		case 'Unpaid':
			return 'red';
		default:
			return 'gray';
	}
}

function getEventBackgroundClass(status) {
	switch (status) {
		case 'Paid':
			return 'bg-green-50 border-green-200';
		case 'Pending':
			return 'bg-yellow-50 border-yellow-200';
		case 'Unpaid':
			return 'bg-red-50 border-red-200';
		default:
			return 'bg-gray-50 border-gray-200';
	}
}

function formatAmount(event) {
	try {
		if (event.midtrans_transaction_object) {
			const transactionData = JSON.parse(event.midtrans_transaction_object);
			const amount = transactionData.gross_amount;
			if (amount) {
				const currency = team.doc.currency === 'IDR' ? 'Rp' : '$';
				return `${currency} ${Number(amount).toLocaleString()}`;
			}
		}
	} catch (e) {
		// Ignore parsing errors
	}
	return 'N/A';
}

function formatDate(dateString) {
	return new Date(dateString).toLocaleDateString('en-US', {
		year: 'numeric',
		month: 'short',
		day: 'numeric',
		hour: '2-digit',
		minute: '2-digit'
	});
}

function printInvoice(invoiceName) {
	// Generate and download Midtrans invoice PDF
	window.open(`/api/method/press.api.billing.get_midtrans_invoice_pdf?invoice_name=${invoiceName}`, '_blank');
}

function showPaymentInstructions(event) {
	try {
		if (event.midtrans_transaction_object) {
			const transactionData = JSON.parse(event.midtrans_transaction_object);
			
			// Only show dialog for bank_transfer type for now, as that's what the dialog supports
			if (transactionData.payment_type === 'bank_transfer' && transactionData.va_numbers && transactionData.va_numbers.length > 0) {
				const vaNumber = transactionData.va_numbers[0];
				selectedPaymentData.value = {
					bank: vaNumber.bank,
					va_number: vaNumber.va_number,
					amount: parseInt(transactionData.gross_amount),
					transaction_id: transactionData.transaction_id,
					status: transactionData.transaction_status,
					expiry_time: transactionData.expiry_time
				};
				showPaymentInstructionsDialog.value = true;
			} else {
				// Fallback for other payment types
				let instructions = '';
				if (transactionData.payment_type === 'cstore') {
					instructions = `Convenience Store Payment:\n\n` +
						`Payment Code: ${transactionData.payment_code}\n` +
						`Store: ${transactionData.store}\n` +
						`Amount: ${transactionData.gross_amount}\n\n` +
						`Please visit the convenience store and provide the payment code.`;
				} else if (transactionData.payment_type === 'qris') {
					instructions = `QRIS Payment Instructions:\n\n` +
						`Please scan the QR code to complete payment.\n` +
						`Amount: ${transactionData.gross_amount}`;
				} else {
					instructions = `Payment Instructions:\n\n` +
						`Payment Type: ${transactionData.payment_type}\n` +
						`Amount: ${transactionData.gross_amount}\n` +
						`Transaction ID: ${transactionData.transaction_id}\n\n` +
						`Please check your payment method for further instructions.`;
				}
				alert(instructions);
			}
		} else {
			alert('Payment instructions not available for this transaction.');
		}
	} catch (e) {
		alert('Error reading payment instructions. Please contact support.');
	}
}

function handlePaymentCompleted(response) {
	// Refresh the payment events list when payment is completed
	paymentEvents.reload();
	showPaymentInstructionsDialog.value = false;
}
</script>