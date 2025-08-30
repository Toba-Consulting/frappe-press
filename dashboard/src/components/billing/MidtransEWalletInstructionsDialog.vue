<template>
	<Dialog :options="{ title: 'E-Wallet Payment Instructions', size: '2xl' }" v-model="show">
		<template #body-content>
			<div class="px-4 pb-4">
				<div class="mb-6">
					<div class="flex items-center space-x-3 mb-4">
						<div class="w-12 h-12 rounded-lg flex items-center justify-center" :class="getWalletStyling(paymentData?.ewallet).containerClass">
							<span class="text-white font-bold text-sm">{{ getWalletIcon(paymentData?.ewallet) }}</span>
						</div>
						<div>
							<h3 class="text-xl font-semibold text-gray-800">{{ getWalletDisplayName() }} Payment</h3>
							<p class="text-sm text-gray-600">Complete your payment using {{ getWalletDisplayName() }}</p>
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
					<!-- QR Code Section (for GoPay and QRIS) -->
					<div v-if="paymentData.qr_code" class="bg-gray-50 border border-gray-200 rounded-lg p-4">
						<h4 class="font-semibold text-gray-800 mb-3 flex items-center">
							<svg class="w-5 h-5 mr-2 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v1m6 11h2m-6 0h-2v4m0-11v3m0 0h.01M12 12h4.01M16 20h4M4 12h4m12 0h.01M5 8h2a1 1 0 001-1V5a1 1 0 00-1-1H5a1 1 0 00-1 1v2a1 1 0 001 1zm12 0h2a1 1 0 001-1V5a1 1 0 00-1-1h-2a1 1 0 00-1 1v2a1 1 0 001 1zM5 20h2a1 1 0 001-1v-2a1 1 0 00-1-1H5a1 1 0 00-1 1v2a1 1 0 001 1z"></path>
							</svg>
							Scan QR Code
						</h4>
						
						<div class="flex flex-col items-center space-y-4">
							<div class="bg-white p-4 rounded-lg border">
								<img :src="paymentData.qr_code" alt="Payment QR Code" class="w-48 h-48" ref="qrImageRef" />
							</div>
							<Button 
								size="sm" 
								variant="ghost" 
								@click="saveQRImage"
								class="text-green-600 hover:text-green-700"
							>
								<svg class="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
									<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path>
								</svg>
								Save QR Image
							</Button>
						</div>
					</div>

					<!-- Deep Link Section (for mobile apps) -->
					<div v-if="paymentData.deeplink" class="bg-gray-50 border border-gray-200 rounded-lg p-4">
						<h4 class="font-semibold text-gray-800 mb-3 flex items-center">
							<svg class="w-5 h-5 mr-2 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 18h.01M8 21h8a2 2 0 002-2V5a2 2 0 00-2-2H8a2 2 0 00-2 2v14a2 2 0 002 2z"></path>
							</svg>
							Mobile App Payment
						</h4>
						
						<div class="text-center">
							<p class="text-sm text-gray-600 mb-4">
								Tap the button below to open {{ getWalletDisplayName() }} app and complete payment
							</p>
							<Button 
								variant="solid" 
								size="lg"
								@click="openDeeplink"
								:class="getWalletStyling(paymentData?.ewallet).buttonClass"
							>
								<svg class="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
									<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 18h.01M8 21h8a2 2 0 002-2V5a2 2 0 00-2-2H8a2 2 0 00-2 2v14a2 2 0 002 2z"></path>
								</svg>
								Open {{ getWalletDisplayName() }} App
							</Button>
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
								v-for="(instruction, index) in getWalletInstructions()" 
								:key="index"
								class="flex items-start space-x-3"
							>
								<div 
									class="w-6 h-6 text-white rounded-full flex items-center justify-center flex-shrink-0 mt-0.5"
									:class="getWalletStyling(paymentData?.ewallet).instructionClass"
								>
									<span class="text-xs font-semibold">{{ index + 1 }}</span>
								</div>
								<div>
									<p class="font-medium text-gray-800">{{ instruction }}</p>
								</div>
							</div>
						</div>
					</div>

					<!-- Payment Details -->
					<div class="bg-gray-50 border border-gray-200 rounded-lg p-4">
						<h4 class="font-semibold text-gray-800 mb-3 flex items-center">
							<svg class="w-5 h-5 mr-2 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path>
							</svg>
							Payment Details
						</h4>
						
						<div class="space-y-3">
							<div class="flex justify-between items-center">
								<span class="text-sm text-gray-600">Transaction ID</span>
								<div class="flex items-center space-x-2">
									<span class="font-mono text-sm text-gray-800">{{ paymentData.transaction_id }}</span>
									<Button 
										size="sm" 
										variant="ghost" 
										@click="copyToClipboard(paymentData.transaction_id)"
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
								<span class="font-semibold text-gray-800">{{ formatCurrency(paymentData.amount) }}</span>
							</div>
							
							<div v-if="paymentData.expiry_time" class="flex justify-between items-center">
								<span class="text-sm text-gray-600">Expires</span>
								<span class="text-sm text-gray-600">{{ formatExpiry(paymentData.expiry_time) }}</span>
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
								<p class="text-sm text-yellow-700">Complete the payment in your {{ getWalletDisplayName() }} app.</p>
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
import { ref, inject, computed } from 'vue';
import { toast } from 'vue-sonner';

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
const qrImageRef = ref(null);

const show = computed({
	get: () => props.modelValue,
	set: (value) => emit('update:modelValue', value)
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

const openDeeplink = () => {
	if (props.paymentData?.deeplink) {
		window.open(props.paymentData.deeplink, '_blank');
	}
};

const saveQRImage = async () => {
	if (!props.paymentData?.qr_code) {
		toast.error('No QR code available to save');
		return;
	}

	// Generate filename with wallet name and timestamp
	const walletName = getWalletDisplayName();
	const timestamp = new Date().toISOString().slice(0, 19).replace(/:/g, '-');
	const filename = `${walletName}-QR-${timestamp}.png`;

	try {
		// Simple approach: Direct download link
		const link = document.createElement('a');
		link.href = props.paymentData.qr_code;
		link.download = filename;
		link.target = '_blank';
		link.rel = 'noopener noreferrer';
		
		// Add to DOM, click, and remove
		document.body.appendChild(link);
		link.click();
		document.body.removeChild(link);
		
		toast.success('QR code download started!');
		
	} catch (error) {
		console.error('Download failed:', error);
		
		// Fallback: Open in new tab
		try {
			const newWindow = window.open(props.paymentData.qr_code, '_blank', 'noopener,noreferrer');
			
			if (newWindow) {
				toast.info('QR image opened in new tab. Right-click to save as "' + filename + '"');
			} else {
				toast.error('Unable to open QR image. Please check your popup settings.');
			}
		} catch (fallbackError) {
			toast.error('Failed to access QR image');
		}
	}
};

// Dynamic E-Wallet functionality
const getWalletStyling = (walletCode) => {
	const walletStyles = {
		'GOPAY': {
			containerClass: 'bg-green-600',
			instructionClass: 'bg-green-600',
			buttonClass: 'bg-green-600 hover:bg-green-700'
		},
		'OVO': {
			containerClass: 'bg-purple-600',
			instructionClass: 'bg-purple-600',
			buttonClass: 'bg-purple-600 hover:bg-purple-700'
		},
		'DANA': {
			containerClass: 'bg-blue-600',
			instructionClass: 'bg-blue-600',
			buttonClass: 'bg-blue-600 hover:bg-blue-700'
		},
		'SHOPEEPAY': {
			containerClass: 'bg-orange-600',
			instructionClass: 'bg-orange-600',
			buttonClass: 'bg-orange-600 hover:bg-orange-700'
		},
		'QRIS': {
			containerClass: 'bg-gray-600',
			instructionClass: 'bg-gray-600',
			buttonClass: 'bg-gray-600 hover:bg-gray-700'
		}
	};
	
	return walletStyles[walletCode?.toUpperCase()] || walletStyles['GOPAY'];
};

const getWalletDisplayName = () => {
	const walletNames = {
		'GOPAY': 'GoPay',
		'OVO': 'OVO',
		'DANA': 'DANA',
		'SHOPEEPAY': 'ShopeePay',
		'QRIS': 'QRIS'
	};
	
	const walletCode = props.paymentData?.ewallet?.toUpperCase() || 'GOPAY';
	return walletNames[walletCode] || walletCode;
};

const getWalletIcon = (walletCode) => {
	const walletIcons = {
		'GOPAY': 'GP',
		'OVO': 'OVO',
		'DANA': 'DA',
		'SHOPEEPAY': 'SP',
		'QRIS': 'QR'
	};
	
	return walletIcons[walletCode?.toUpperCase()] || 'EW';
};

const getWalletInstructions = () => {
	const walletCode = props.paymentData?.ewallet?.toUpperCase() || 'GOPAY';
	
	const instructions = {
		'GOPAY': [
			"Open your Gojek app",
			"Tap 'GoPay' on the home screen",
			"Scan the QR code or tap 'Open GoPay App' button",
			"Confirm the payment amount",
			"Enter your GoPay PIN to complete the payment"
		],
		'OVO': [
			"Open your OVO app",
			"Tap the 'Pay/Top Up' button",
			"Tap 'Open OVO App' button or scan QR code if available",
			"Confirm the payment details",
			"Enter your OVO PIN to complete the payment"
		],
		'DANA': [
			"Open your DANA app",
			"Tap 'Scan' on the home screen",
			"Scan the QR code or tap 'Open DANA App' button",
			"Confirm the payment amount and details",
			"Enter your DANA PIN to complete the payment"
		],
		'SHOPEEPAY': [
			"Open your Shopee app",
			"Tap 'ShopeePay' on the home screen",
			"Tap 'Open ShopeePay App' button or scan QR code if available",
			"Confirm the payment amount and details",
			"Enter your ShopeePay PIN to complete the payment"
		],
		'QRIS': [
			"Open any QRIS-compatible app (GoPay, OVO, DANA, etc.)",
			"Tap the QR scan feature",
			"Scan the QRIS code displayed above",
			"Confirm the payment amount and merchant details",
			"Complete the payment using your preferred method"
		]
	};
	
	return instructions[walletCode] || instructions['GOPAY'];
};
</script>