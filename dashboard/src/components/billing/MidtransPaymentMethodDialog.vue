<template>
	<Dialog :options="{ title: 'Select Payment Method', size: 'xl' }" v-model="show">
		<template #body-content>
			<div class="px-4 pb-4">
				<div class="mb-4">
					<h3 class="text-lg font-semibold text-gray-800">Choose your preferred payment method</h3>
					<p class="text-sm text-gray-600 mt-1">Amount: {{ formatCurrency(amount) }}</p>
				</div>

				<div class="space-y-3">
					<!-- Bank Transfer -->
					<div
						class="border rounded-lg p-4 cursor-pointer transition-all duration-200 hover:border-blue-500 hover:bg-blue-50"
						:class="{
							'border-blue-500 bg-blue-50': selectedMethod === 'bank_transfer',
							'border-gray-200': selectedMethod !== 'bank_transfer'
						}"
						@click="selectPaymentMethod('bank_transfer')"
					>
						<div class="flex items-center justify-between">
							<div class="flex items-center space-x-3">
								<div class="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center">
									<svg class="w-6 h-6 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
										<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4"></path>
									</svg>
								</div>
								<div>
									<h4 class="font-semibold text-gray-800">Bank Transfer</h4>
									<p class="text-sm text-gray-600">Transfer directly to our bank account</p>
								</div>
							</div>
							<div class="w-5 h-5">
								<div 
									class="w-5 h-5 rounded-full border-2 flex items-center justify-center"
									:class="{
										'border-blue-500 bg-blue-500': selectedMethod === 'bank_transfer',
										'border-gray-300': selectedMethod !== 'bank_transfer'
									}"
								>
									<div v-if="selectedMethod === 'bank_transfer'" class="w-2 h-2 bg-white rounded-full"></div>
								</div>
							</div>
						</div>
					</div>

					<!-- E-Wallet -->
					<div
						class="border rounded-lg p-4 cursor-pointer transition-all duration-200 hover:border-green-500 hover:bg-green-50"
						:class="{
							'border-green-500 bg-green-50': selectedMethod === 'ewallet',
							'border-gray-200': selectedMethod !== 'ewallet'
						}"
						@click="selectPaymentMethod('ewallet')"
					>
						<div class="flex items-center justify-between">
							<div class="flex items-center space-x-3">
								<div class="w-10 h-10 bg-green-100 rounded-lg flex items-center justify-center">
									<svg class="w-6 h-6 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
										<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 18h.01M8 21h8a2 2 0 002-2V5a2 2 0 00-2-2H8a2 2 0 00-2 2v14a2 2 0 002 2z"></path>
									</svg>
								</div>
								<div>
									<h4 class="font-semibold text-gray-800">E-Wallet</h4>
									<p class="text-sm text-gray-600">GoPay, QRIS</p>
								</div>
							</div>
							<div class="w-5 h-5">
								<div 
									class="w-5 h-5 rounded-full border-2 flex items-center justify-center"
									:class="{
										'border-green-500 bg-green-500': selectedMethod === 'ewallet',
										'border-gray-300': selectedMethod !== 'ewallet'
									}"
								>
									<div v-if="selectedMethod === 'ewallet'" class="w-2 h-2 bg-white rounded-full"></div>
								</div>
							</div>
						</div>
					</div>
				</div>

				<div class="mt-6 flex justify-end space-x-3">
					<Button variant="ghost" @click="show = false">
						Cancel
					</Button>
					<Button 
						variant="solid" 
						:disabled="!selectedMethod"
						@click="proceedWithPaymentMethod"
					>
						Continue
					</Button>
				</div>
			</div>
		</template>
	</Dialog>
</template>

<script setup>
import { Dialog, Button } from 'frappe-ui';
import { ref, inject, computed } from 'vue';

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

const emit = defineEmits(['update:modelValue', 'methodSelected']);

const team = inject('team');
const selectedMethod = ref(null);

const show = computed({
	get: () => props.modelValue,
	set: (value) => emit('update:modelValue', value)
});

const selectPaymentMethod = (method) => {
	selectedMethod.value = method;
};

const proceedWithPaymentMethod = () => {
	if (selectedMethod.value) {
		emit('methodSelected', {
			method: selectedMethod.value,
			amount: props.amount
		});
		show.value = false;
	}
};

const formatCurrency = (amount) => {
	const currency = team.doc?.currency || 'USD';
	const currencySymbol = currency === 'IDR' ? 'Rp ' : '$';
	return currencySymbol + amount.toLocaleString();
};
</script>