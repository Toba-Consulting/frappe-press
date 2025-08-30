<template>
	<Dialog :options="{ title: 'Select E-Wallet Provider', size: 'xl' }" v-model="show">
		<template #body-content>
			<div class="px-4 pb-4">
				<div class="mb-4">
					<h3 class="text-lg font-semibold text-gray-800">Choose your E-Wallet provider</h3>
					<p class="text-sm text-gray-600 mt-1">Amount: {{ formatCurrency(amount) }}</p>
				</div>

				<div class="space-y-3">
					<!-- GoPay (Disabled) -->
					<div class="border rounded-lg p-4 opacity-50 cursor-not-allowed border-gray-200 bg-gray-50">
						<div class="flex items-center justify-between">
							<div class="flex items-center space-x-4">
								<div class="grayscale">
									<GoPayIcon />
								</div>
								<div>
									<h4 class="font-semibold text-gray-400">GoPay</h4>
									<p class="text-xs text-gray-400">Currently unavailable</p>
								</div>
							</div>
							<div class="w-5 h-5 rounded-full border-2 border-gray-300"></div>
						</div>
					</div>

					<!-- QRIS -->
					<div
						class="border rounded-lg p-4 cursor-pointer transition-all duration-200 hover:border-blue-500 hover:bg-blue-50"
						:class="{
							'border-gray-600 bg-gray-50': selectedWallet === 'qris',
							'border-gray-200': selectedWallet !== 'qris'
						}"
						@click="selectWallet('qris')"
					>
						<div class="flex items-center justify-between">
							<div class="flex items-center space-x-4">
								<div class="w-12 h-12 bg-gray-100 rounded-lg flex items-center justify-center">
									<QRISIcon />
								</div>
								<div>
									<h4 class="font-semibold text-gray-800">QRIS</h4>
									<p class="text-xs text-green-600 mt-1">✓ Scan QR code to pay</p>
								</div>
							</div>
							<div class="w-5 h-5">
								<div 
									class="w-5 h-5 rounded-full border-2 flex items-center justify-center"
									:class="{
										'border-green-500 bg-green-500': selectedWallet === 'qris',
										'border-gray-300': selectedWallet !== 'qris'
									}"
								>
									<div v-if="selectedWallet === 'qris'" class="w-2 h-2 bg-white rounded-full"></div>
								</div>
							</div>
						</div>
					</div>
				</div>

				<div class="mt-6 flex justify-between">
					<Button variant="ghost" @click="goBack" class="flex items-center whitespace-nowrap">
						<svg class="w-4 h-4 mr-1 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7"></path>
						</svg>
					</Button>
					<div class="flex space-x-3">
						<Button variant="ghost" @click="show = false">
							Cancel
						</Button>
						<Button 
							variant="solid" 
							:disabled="!selectedWallet"
							@click="proceedWithWallet"
							:loading="creatingPayment"
						>
							{{ creatingPayment ? 'Creating Payment...' : 'Proceed Now' }}
						</Button>
					</div>
				</div>
			</div>
		</template>
	</Dialog>
</template>

<script setup>
import { Dialog, Button } from 'frappe-ui';
import { ref, inject, computed } from 'vue';
import GoPayIcon from '../icons/GoPayIcon.vue'
import QRISIcon from '../icons/QRISIcon.vue'

const props = defineProps({
	modelValue: {
		type: Boolean,
		default: false
	},
	amount: {
		type: Number,
		required: true
	}
});

const emit = defineEmits(['update:modelValue', 'walletSelected', 'goBack']);

const team = inject('team');
const selectedWallet = ref(null);
const creatingPayment = ref(false);

const show = computed({
	get: () => props.modelValue,
	set: (value) => emit('update:modelValue', value)
});

const selectWallet = (wallet) => {
	selectedWallet.value = wallet;
};

const proceedWithWallet = async () => {
	if (selectedWallet.value) {
		creatingPayment.value = true;
		
		try {
			emit('walletSelected', {
				wallet: selectedWallet.value,
				amount: props.amount
			});
			show.value = false;
		} finally {
			creatingPayment.value = false;
		}
	}
};

const goBack = () => {
	emit('goBack');
};

const formatCurrency = (amount) => {
	const currency = team.doc?.currency || 'USD';
	const currencySymbol = currency === 'IDR' ? 'Rp ' : '$';
	return currencySymbol + amount.toLocaleString();
};
</script>