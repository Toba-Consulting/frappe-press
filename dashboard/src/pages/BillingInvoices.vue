<template>
	<div class="p-5">
		<ObjectList :options="options" />
		<Dialog
			v-model="invoiceDialog"
			:options="{ size: '3xl', title: showInvoice?.name }"
		>
			<template #body-content>
				<template v-if="showInvoice">
					<div
						v-if="showInvoice.status === 'Empty'"
						class="text-base text-gray-600"
					>
						Nothing to show
					</div>
					<InvoiceTable v-else :invoiceId="showInvoice.name" />
				</template>
			</template>
		</Dialog>
		<AddPrepaidCreditsDialog
			v-if="showBuyPrepaidCreditsDialog"
			v-model="showBuyPrepaidCreditsDialog"
			:minimumAmount="minimumAmount"
			@success="
				() => {
					showBuyPrepaidCreditsDialog = false;
				}
			"
		/>
		<MidtransPaymentInstructionsDialog
			v-if="showPaymentInstructionsDialog"
			v-model="showPaymentInstructionsDialog"
			:paymentData="selectedPaymentData"
			@paymentCompleted="handlePaymentCompleted"
		/>
	</div>
</template>
<script>
import { h } from 'vue';
import { Button, call } from 'frappe-ui';
import ObjectList from '../components/ObjectList.vue';
import InvoiceTable from '../components/InvoiceTable.vue';
import { userCurrency, date } from '../utils/format';
import { confirmDialog, icon, renderInDialog } from '../utils/components';
import AddPrepaidCreditsDialog from '../components/billing/AddPrepaidCreditsDialog.vue';
import MidtransPaymentInstructionsDialog from '../components/billing/MidtransPaymentInstructionsDialog.vue';
import { dayjsLocal } from '../utils/dayjs';
import router from '../router';

export default {
	name: 'BillingInvoices',
	props: ['tab'],
	components: {
		ObjectList,
		InvoiceTable,
		AddPrepaidCreditsDialog,
		MidtransPaymentInstructionsDialog,
	},
	data() {
		return {
			invoiceDialog: false,
			showInvoice: null,
			showBuyPrepaidCreditsDialog: false,
			minimumAmount: 0,
			showPaymentInstructionsDialog: false,
			selectedPaymentData: null,
		};
	},
	computed: {
		options() {
			return {
				doctype: 'Invoice',
				fields: [
					'type',
					'invoice_pdf',
					'payment_mode',
					'stripe_invoice_url',
					'due_date',
					'period_start',
					'period_end',
					'mpesa_invoice',
					'mpesa_invoice_pdf',
				],
				filterControls: () => {
					return [
						{
							type: 'select',
							label: 'Type',
							class: !this.$isMobile ? 'w-36' : '',
							fieldname: 'type',
							options: ['', 'Subscription', 'Prepaid Credits'],
						},
						{
							type: 'select',
							label: 'Status',
							class: !this.$isMobile ? 'w-36' : '',
							fieldname: 'status',
							options: [
								'',
								'Draft',
								'Invoice Created',
								'Unpaid',
								'Paid',
								'Refunded',
								'Uncollectible',
								'Collected',
								'Empty',
							],
						},
					];
				},
				columns: [
					{
						label: 'Invoice',
						fieldname: 'name',
						class: 'font-medium',
						format(value, row) {
							if (row.type == 'Subscription') {
								let end = dayjsLocal(row.period_end);
								return end.format('MMMM YYYY');
							} else if (row.type == 'Partnership Fees') {
								return 'Partnership Fees';
							}
							return 'Prepaid Credits';
						},
						width: 0.8,
					},
					{
						label: 'Status',
						fieldname: 'status',
						type: 'Badge',
						width: '150px',
					},
					{
						label: 'Date',
						fieldname: 'due_date',
						format(value, row) {
							if (row.type == 'Subscription') {
								let start = dayjsLocal(row.period_start);
								let end = dayjsLocal(row.period_end);
								let sameYear = start.year() === end.year();
								let formattedStart = sameYear
									? start.format('MMM D')
									: start.format('ll');
								return `${formattedStart} - ${end.format('ll')}`;
							}
							return date(value, 'll');
						},
					},
					{
						label: 'Total',
						fieldname: 'total',
						format: this.formatCurrency,
						align: 'right',
						width: 0.6,
					},
					{
						label: 'Amount Paid',
						fieldname: 'amount_paid',
						format: this.formatCurrency,
						align: 'right',
						width: 0.6,
					},
					{
						label: 'Amount Due',
						fieldname: 'amount_due',
						format: this.formatCurrency,
						align: 'right',
						width: 0.6,
					},
					{
						label: '',
						type: 'Button',
						align: 'right',
						Button: ({ row }) => {
							if (row.invoice_pdf || row.mpesa_invoice_pdf) {
								return {
									label: 'Download Invoice',
									slots: {
										prefix: icon('download'),
									},
									onClick: () => {
										if (row.mpesa_invoice_pdf) {
											window.open(row.mpesa_invoice_pdf);
										} else {
											window.open(row.invoice_pdf);
										}
									},
								};
							}
							if (row.status === 'Unpaid' && row.amount_due > 0) {
								return {
									label: 'Pay Now',
									slots: {
										prefix: icon('external-link'),
									},
									onClick: (e) => {
										e.stopPropagation();
										if (row.stripe_invoice_url && row.payment_mode == 'Card') {
											window.open(
												`/api/method/press.api.client.run_doc_method?dt=Invoice&dn=${row.name}&method=stripe_payment_url`,
											);
										} else {
											// For all non-Stripe payments, check for pending Midtrans payments first
											this.checkPendingPayment(row);
										}
									},
								};
							}
						},
						prefix(row) {
							if (row.stripe_payment_failed && row.status !== 'Paid') {
								return h(Button, {
									variant: 'ghost',
									theme: 'red',
									icon: 'alert-circle',
									onClick(e) {
										e.stopPropagation();
										confirmDialog({
											title: 'Payment Failed',
											message: `<div class="space-y-4"><p class="text-base">Your payment with the card ending <strong>${row.stripe_payment_failed_card}</strong> failed for this invoice due to the following reason:</p><div class="text-sm font-mono text-gray-600 rounded p-2 bg-gray-100">${row.stripe_payment_error}</div><p class="text-base">Please change your payment method to pay this invoice.</p></div>`,
											primaryAction: {
												label: 'Change Payment Method',
												variant: 'solid',
												onClick: ({ hide }) => {
													hide();
													router.push({
														name: 'BillingPaymentMethods',
													});
												},
											},
										});
									},
								});
							}
						},
					},
				],
				orderBy: 'due_date desc, creation desc',
				onRowClick: (row) => {
					this.showInvoice = row;
					this.invoiceDialog = true;
				},
			};
		},
	},
	methods: {
		formatCurrency(value) {
			if (value === 0) {
				return '';
			}
			return userCurrency(value);
		},
		async checkPendingPayment(invoice) {
			try {
				// Check for pending Midtrans payment events for this invoice
				const response = await call('frappe.client.get_list', {
					doctype: 'Midtrans Payment Event',
					fields: ['name', 'midtrans_transaction_object', 'payment_status'],
					filters: {
						invoice: invoice.name,
						payment_status: 'Pending'
					},
					order_by: 'creation desc',
					limit: 1
				});

				if (response && response.length > 0) {
					const pendingPayment = response[0];
					this.showPaymentInstructions(pendingPayment);
				} else {
					// No pending payment found, show buy credits dialog
					this.showBuyPrepaidCreditsDialog = true;
					this.minimumAmount = invoice.amount_due;
				}
			} catch (error) {
				console.error('Error checking pending payment:', error);
				// Fallback to buy credits dialog
				this.showBuyPrepaidCreditsDialog = true;
				this.minimumAmount = invoice.amount_due;
			}
		},
		showPaymentInstructions(paymentEvent) {
			try {
				if (paymentEvent.midtrans_transaction_object) {
					const transactionData = JSON.parse(paymentEvent.midtrans_transaction_object);
					
					// Only show dialog for bank_transfer type
					if (transactionData.payment_type === 'bank_transfer' && transactionData.va_numbers && transactionData.va_numbers.length > 0) {
						const vaNumber = transactionData.va_numbers[0];
						this.selectedPaymentData = {
							bank: vaNumber.bank.toUpperCase(),
							va_number: vaNumber.va_number,
							amount: parseInt(transactionData.gross_amount),
							transaction_id: transactionData.transaction_id,
							status: transactionData.transaction_status,
							expiry_time: transactionData.expiry_time
						};
						this.showPaymentInstructionsDialog = true;
					} else {
						// For other payment types, show alert
						alert(`Pending ${transactionData.payment_type} payment found. Please complete your existing payment before creating a new one.`);
					}
				}
			} catch (e) {
				console.error('Error parsing payment data:', e);
				alert('Found pending payment but unable to show instructions. Please check Payment History.');
			}
		},
		handlePaymentCompleted() {
			// Refresh the page or handle payment completion
			this.showPaymentInstructionsDialog = false;
			// You might want to reload the invoice list here
			window.location.reload();
		},
	},
};
</script>
