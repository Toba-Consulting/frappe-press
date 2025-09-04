<template>
	<Dialog :options="{ title: 'Bank Transfer Instructions', size: '2xl' }" v-model="show">
		<template #body-content>
			<div class="px-4 pb-4">
				<div class="mb-6">
					<div class="flex items-center space-x-3 mb-4">
						<div class="w-12 h-12 rounded-lg flex items-center justify-center bg-white border border-gray-200">
							<component :is="bankIconComponent" class="w-10 h-10" />
						</div>
						<div>
							<h3 class="text-xl font-semibold text-gray-800">{{ getBankDisplayName() }} Bank Transfer</h3>
							<p class="text-sm text-gray-600">Complete your payment using {{ getBankDisplayName() }} bank transfer</p>
						</div>
					</div>
					
					<div class="bg-blue-50 border border-blue-200 rounded-lg p-4">
						<div class="flex items-center space-x-2">
							<div class="w-6 h-6 bg-blue-100 rounded-full flex items-center justify-center">
								<span class="text-blue-600 text-sm font-semibold">!</span>
							</div>
							<div>
								<p class="text-sm text-blue-800 font-medium">Payment Amount</p>
								<p class="text-lg font-bold text-blue-900">{{ formatCurrency(paymentData?.amount) }}</p>
							</div>
						</div>
					</div>
				</div>

				<div v-if="paymentData" class="space-y-6">
					<!-- Virtual Account Details -->
					<div class="bg-gray-50 border border-gray-200 rounded-lg p-4">
						<h4 class="font-semibold text-gray-800 mb-3 flex items-center">
							<svg class="w-5 h-5 mr-2 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4"></path>
							</svg>
							Virtual Account Details
						</h4>
						
						<div class="space-y-3">
							<div class="flex justify-between items-center">
								<span class="text-sm text-gray-600">Virtual Account Number</span>
								<div class="flex items-center space-x-2">
									<span class="font-mono text-lg font-semibold text-gray-800">{{ paymentData.va_number }}</span>
									<Button 
										size="sm" 
										variant="ghost" 
										@click="copyToClipboard(paymentData.va_number)"
										class="text-blue-600 hover:text-blue-700"
									>
										<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
											<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 5H6a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2v-1M8 5a2 2 0 002 2h2a2 2 0 002-2M8 5a2 2 0 012-2h2a2 2 0 012 2m0 0h2a2 2 0 012 2v3m2 4H10m0 0l3-3m-3 3l3 3"></path>
										</svg>
									</Button>
								</div>
							</div>
							
							<div class="flex justify-between items-center">
								<span class="text-sm text-gray-600">Amount</span>
								<div class="flex items-center space-x-2">
									<span class="font-semibold text-gray-800">{{ formatCurrency(paymentData.amount) }}</span>
									<Button 
										size="sm" 
										variant="ghost" 
										@click="copyToClipboard(paymentData.amount.toString())"
										class="text-blue-600 hover:text-blue-700"
									>
										<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
											<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 5H6a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2v-1M8 5a2 2 0 002 2h2a2 2 0 002-2M8 5a2 2 0 012-2h2a2 2 0 012 2m0 0h2a2 2 0 012 2v3m2 4H10m0 0l3-3m-3 3l3 3"></path>
										</svg>
									</Button>
								</div>
							</div>
							
							<div class="flex justify-between items-center">
								<span class="text-sm text-gray-600">Expires</span>
								<span class="text-sm text-gray-600">{{ formatExpiry(paymentData.expiry_time) }}</span>
							</div>
						</div>
					</div>

					<!-- Payment Instructions -->
					<div class="space-y-4">
						<h4 class="font-semibold text-gray-800 flex items-center">
							<svg class="w-5 h-5 mr-2 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v10a2 2 0 002 2h8a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"></path>
							</svg>
							Payment Instructions
						</h4>
						
						<div class="space-y-3">
							<div 
								v-for="(instruction, index) in bankInstructions" 
								:key="index"
								class="flex items-start space-x-3"
							>
								<div 
									class="w-6 h-6 text-white rounded-full flex items-center justify-center flex-shrink-0 mt-0.5"
									:class="getBankStyling(paymentData?.bank).instructionClass"
								>
									<span class="text-xs font-semibold">{{ index + 1 }}</span>
								</div>
								<div>
									<p class="font-medium text-gray-800">
										<span v-if="instruction.includes('Virtual Account Number') && paymentData?.va_number">
											{{ instruction.replace('Virtual Account Number', '') }}
											<span class="font-mono bg-gray-100 px-2 py-1 rounded text-blue-600">{{ paymentData.va_number }}</span>
										</span>
										<span v-else-if="instruction.includes('exact amount') && paymentData?.amount">
											{{ instruction.replace('exact amount', '') }}
											<span class="font-semibold bg-gray-100 px-2 py-1 rounded text-green-600">{{ formatCurrency(paymentData.amount) }}</span>
										</span>
										<span v-else>
											{{ instruction }}
										</span>
									</p>
								</div>
							</div>
						</div>
					</div>

					<!-- Status Check -->
					<div class="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
						<div class="flex items-center space-x-3">
							<div class="w-8 h-8 bg-yellow-100 rounded-full flex items-center justify-center">
								<svg class="w-5 h-5 text-yellow-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
									<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"></path>
								</svg>
							</div>
							<div>
								<p class="font-medium text-yellow-800">Payment Status: {{ getPaymentStatus() }}</p>
								<p class="text-sm text-yellow-700">We'll automatically verify your payment and add credits to your account.</p>
							</div>
						</div>
					</div>
				</div>

				<div class="mt-6 flex justify-between">
					<Button variant="ghost" @click="checkPaymentStatus" :loading="checkingStatus">
						<svg class="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"></path>
						</svg>
						Check Payment Status
					</Button>
					<Button variant="solid" @click="closeDialog">
						Done
					</Button>
				</div>
			</div>
		</template>
	</Dialog>
</template>

<script setup>
import { Dialog, Button, call } from 'frappe-ui';
import { ref, inject, computed, watch } from 'vue';
import { toast } from 'vue-sonner';
import BCAIcon from '../icons/BCAIcon.vue';
import BNIIcon from '../icons/BNIIcon.vue';
import BRIIcon from '../icons/BRIIcon.vue';
import CIMBIcon from '../icons/CIMBIcon.vue';
import MandiriIcon from '../icons/MandiriIcon.vue';

const props = defineProps({
	modelValue: {
		type: Boolean,
		default: false
	},
	paymentData: {
		type: Object,
		default: null
	}
});

const emit = defineEmits(['update:modelValue', 'paymentCompleted']);

const team = inject('team');
const checkingStatus = ref(false);
const bankInstructions = ref([]);

const show = computed({
	get: () => props.modelValue,
	set: (value) => emit('update:modelValue', value)
});

const bankIconComponent = computed(() => {
	const bankCode = props.paymentData?.bank?.toUpperCase();
	const iconMap = {
		'BCA': BCAIcon,
		'BNI': BNIIcon,
		'BRI': BRIIcon,
		'CIMB': CIMBIcon,
		'MANDIRI': MandiriIcon
	};
	return iconMap[bankCode] || BCAIcon; // Default to BCA if bank not found
});

const copyToClipboard = async (text) => {
	try {
		await navigator.clipboard.writeText(text);
		toast.success('Copied to clipboard!');
	} catch (err) {
		console.error('Failed to copy:', err);
		toast.error('Failed to copy to clipboard');
	}
};

const formatCurrency = (amount) => {
	if (amount === undefined || amount === null) return '';
	const currency = team.doc?.currency || 'USD';
	const currencySymbol = currency === 'IDR' ? 'Rp ' : '$';
	return currencySymbol + amount.toLocaleString();
};

const formatExpiry = (expiryTime) => {
	return new Date(expiryTime).toLocaleString();
};

const getPaymentStatus = () => {
	return props.paymentData?.status || 'Waiting for Payment';
};

const checkPaymentStatus = async () => {
	checkingStatus.value = true;
	try {
		const response = await call(
			'press.api.billing.check_midtrans_payment_status',
			{
				transaction_id: props.paymentData.transaction_id
			}
		);
		
		if (response.status === 'settlement' || response.status === 'capture') {
			toast.success('Payment confirmed! Credits have been added to your account.');
			emit('paymentCompleted', response);
			show.value = false;
		} else {
			toast.info(`Payment status: ${response.status}`);
		}
	} catch (error) {
		console.error('Error checking payment status:', error);
		toast.error('Failed to check payment status');
	} finally {
		checkingStatus.value = false;
	}
};

const closeDialog = () => {
	show.value = false;
};

// Dynamic bank functionality
const getBankStyling = (bankCode) => {
	const bankStyles = {
		'BCA': {
			containerClass: 'bg-blue-600',
			instructionClass: 'bg-blue-600'
		},
		'BNI': {
			containerClass: 'bg-orange-600',
			instructionClass: 'bg-orange-600'
		},
		'BRI': {
			containerClass: 'bg-blue-800',
			instructionClass: 'bg-blue-800'
		},
		'MANDIRI': {
			containerClass: 'bg-yellow-600',
			instructionClass: 'bg-yellow-600'
		},
		'PERMATA': {
			containerClass: 'bg-green-600',
			instructionClass: 'bg-green-600'
		},
		'CIMB': {
			containerClass: 'bg-red-600',
			instructionClass: 'bg-red-600'
		}
	};
	
	return bankStyles[bankCode?.toUpperCase()] || bankStyles['BCA'];
};

const getBankDisplayName = () => {
	const bankNames = {
		'BCA': 'Bank Central Asia (BCA)',
		'BNI': 'Bank Negara Indonesia (BNI)', 
		'BRI': 'Bank Rakyat Indonesia (BRI)',
		'MANDIRI': 'Bank Mandiri',
		'PERMATA': 'Bank Permata',
		'CIMB': 'CIMB Niaga'
	};
	
	const bankCode = props.paymentData?.bank?.toUpperCase() || 'BCA';
	return bankNames[bankCode] || bankCode;
};

const loadBankInstructions = async (bankCode) => {
	if (!bankCode) return;
	
	try {
		const response = await call('press.api.billing.get_bank_payment_instructions', {
			bank_code: bankCode
		});
		bankInstructions.value = response.instructions || [];
	} catch (error) {
		console.error('Failed to load bank instructions:', error);
		// Fallback to default BCA instructions
		bankInstructions.value = [
			"Login to your mobile banking or internet banking",
			"Select \"Transfer\" menu", 
			"Choose \"Virtual Account\" as destination",
			"Enter the Virtual Account Number",
			"Enter the exact amount",
			"Confirm and complete the transfer"
		];
	}
};

// Load instructions when payment data changes
watch(() => props.paymentData?.bank, (newBank) => {
	if (newBank) {
		loadBankInstructions(newBank);
	}
}, { immediate: true });

// Load instructions when dialog opens  
watch(() => props.modelValue, (isOpen) => {
	if (isOpen && props.paymentData?.bank) {
		loadBankInstructions(props.paymentData.bank);
	}
});
</script>