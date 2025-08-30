<template>
	<Dialog :options="{ title: 'Select Bank for Transfer', size: 'xl' }" v-model="show">
		<template #body-content>
			<div class="px-4 pb-4">
				<div class="mb-4">
					<h3 class="text-lg font-semibold text-gray-800">Choose your bank for transfer</h3>
					<p class="text-sm text-gray-600 mt-1">Amount: {{ formatCurrency(amount) }}</p>
				</div>

				<div class="space-y-3">
					<!-- BCA Bank -->
					<div
						class="border rounded-lg p-4 cursor-pointer transition-all duration-200 hover:border-blue-500 hover:bg-blue-50"
						:class="{
							'border-blue-600 bg-blue-50': selectedBank === 'bca',
							'border-gray-200': selectedBank !== 'bca'
						}"
						@click="selectBank('bca')"
					>
						<div class="flex items-center justify-between">
							<div class="flex items-center space-x-4">
								<BCAIcon />
								<div>
									<h4 class="font-semibold text-gray-800">Bank Central Asia (BCA)</h4>
									<p class="text-xs text-green-600 mt-1">✓ Instant verification</p>
								</div>
							</div>
							<div class="w-5 h-5">
								<div 
									class="w-5 h-5 rounded-full border-2 flex items-center justify-center"
									:class="{
										'border-blue-500 bg-blue-500': selectedBank === 'bca',
										'border-gray-300': selectedBank !== 'bca'
									}"
								>
									<div v-if="selectedBank === 'bca'" class="w-2 h-2 bg-white rounded-full"></div>
								</div>
							</div>
						</div>
					</div>

					<!--Bank Negara Indonesia (BNI)-->
					<div
						class="border rounded-lg p-4 cursor-pointer transition-all duration-200 hover:border-blue-500 hover:bg-blue-50"
						:class="{
							'border-orange-500 bg-orange-50': selectedBank === 'bni',
							'border-gray-200': selectedBank !== 'bni'
						}"
						@click="selectBank('bni')"
					>
						<div class="flex items-center justify-between">
							<div class="flex items-center space-x-4">
								<BNIIcon />
								<div>
									<h4 class="font-semibold text-gray-800">Bank Negara Indonesia (BNI)</h4>
									<p class="text-xs text-green-600 mt-1">✓ Instant verification</p>
								</div>
							</div>
							<div class="w-5 h-5">
								<div 
									class="w-5 h-5 rounded-full border-2 flex items-center justify-center"
									:class="{
										'border-blue-500 bg-blue-500': selectedBank === 'bni',
										'border-gray-300': selectedBank !== 'bni'
									}"
								>
									<div v-if="selectedBank === 'bni'" class="w-2 h-2 bg-white rounded-full"></div>
								</div>
							</div>
						</div>
					</div>

					<!--Bank Rakyat Indonesia (BRI)-->
					<div
						class="border rounded-lg p-4 cursor-pointer transition-all duration-200 hover:border-blue-500 hover:bg-blue-50"
						:class="{
							'border-blue-800 bg-blue-50': selectedBank === 'bri',
							'border-gray-200': selectedBank !== 'bri'
						}"
						@click="selectBank('bri')"
					>
						<div class="flex items-center justify-between">
							<div class="flex items-center space-x-4">
								<BRIIcon />
								<div>
									<h4 class="font-semibold text-gray-800">Bank Rakyat Indonesia (BRI)</h4>
									<p class="text-xs text-green-600 mt-1">✓ Instant verification</p>
								</div>
							</div>
							<div class="w-5 h-5">
								<div 
									class="w-5 h-5 rounded-full border-2 flex items-center justify-center"
									:class="{
										'border-blue-500 bg-blue-500': selectedBank === 'bri',
										'border-gray-300': selectedBank !== 'bri'
									}"
								>
									<div v-if="selectedBank === 'bri'" class="w-2 h-2 bg-white rounded-full"></div>
								</div>
							</div>
						</div>
					</div>

					<!--Bank Mandiri-->
					<div
						class="border rounded-lg p-4 cursor-pointer transition-all duration-200 hover:border-blue-500 hover:bg-blue-50"
						:class="{
							'border-yellow-500 bg-yellow-50': selectedBank === 'mandiri',
							'border-gray-200': selectedBank !== 'mandiri'
						}"
						@click="selectBank('mandiri')"
					>
						<div class="flex items-center justify-between">
							<div class="flex items-center space-x-4">
								<MandiriIcon />
								<div>
									<h4 class="font-semibold text-gray-800">Mandiri</h4>
									<p class="text-xs text-green-600 mt-1">✓ Instant verification</p>
								</div>
							</div>
							<div class="w-5 h-5">
								<div 
									class="w-5 h-5 rounded-full border-2 flex items-center justify-center"
									:class="{
										'border-blue-500 bg-blue-500': selectedBank === 'mandiri',
										'border-gray-300': selectedBank !== 'mandiri'
									}"
								>
									<div v-if="selectedBank === 'mandiri'" class="w-2 h-2 bg-white rounded-full"></div>
								</div>
							</div>
						</div>
					</div>

					<div
						class="border rounded-lg p-4 cursor-pointer transition-all duration-200 hover:border-blue-500 hover:bg-blue-50"
						:class="{
							'border-red-600 bg-red-50': selectedBank === 'cimb',
							'border-gray-200': selectedBank !== 'cimb'
						}"
						@click="selectBank('cimb')"
					>
						<div class="flex items-center justify-between">
							<div class="flex items-center space-x-4">
								<CIMBIcon />
								<div>
									<h4 class="font-semibold text-gray-800">CIMB</h4>
									<p class="text-xs text-green-600 mt-1">✓ Instant verification</p>
								</div>
							</div>
							<div class="w-5 h-5">
								<div 
									class="w-5 h-5 rounded-full border-2 flex items-center justify-center"
									:class="{
										'border-blue-500 bg-blue-500': selectedBank === 'cimb',
										'border-gray-300': selectedBank !== 'cimb'
									}"
								>
									<div v-if="selectedBank === 'cimb'" class="w-2 h-2 bg-white rounded-full"></div>
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
							:disabled="!selectedBank"
							@click="proceedWithBank"
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
import BCAIcon from '../icons/BCAIcon.vue';
import BNIIcon from '../icons/BNIIcon.vue';
import BRIIcon from '../icons/BRIIcon.vue';
import MandiriIcon from '../icons/MandiriIcon.vue';
import CIMBIcon from '../icons/CIMBIcon.vue';

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

const emit = defineEmits(['update:modelValue', 'bankSelected', 'goBack']);

const team = inject('team');
const selectedBank = ref(null);
const creatingPayment = ref(false);

const show = computed({
	get: () => props.modelValue,
	set: (value) => emit('update:modelValue', value)
});

const selectBank = (bank) => {
	selectedBank.value = bank;
};

const proceedWithBank = async () => {
	if (selectedBank.value) {
		creatingPayment.value = true;
		
		try {
			emit('bankSelected', {
				bank: selectedBank.value,
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