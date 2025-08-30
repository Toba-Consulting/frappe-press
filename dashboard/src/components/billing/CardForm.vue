<template>
	<div class="relative">
		<div
			v-if="!ready"
			class="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-8 transform"
		>
			<Spinner class="h-5 w-5 text-gray-700" />
		</div>
		<div :class="{ 'opacity-0': !ready }">
			<div v-show="!tryingMicroCharge && !processingMidtrans">
				<label class="block" v-if="paymentGateway === 'Stripe'">
					<span class="block text-xs text-gray-600">
						Credit or Debit Card
					</span>
					<div
						class="form-input mt-2 block h-[unset] w-full py-2 pl-3"
						ref="cardElementRef"
					></div>
					<ErrorMessage class="mt-1" :message="cardErrorMessage" />
				</label>
				
				<div v-else-if="paymentGateway === 'Midtrans'" class="block">
					<span class="block text-xs text-gray-600 mb-2">
						Credit or Debit Card
					</span>
					<div class="space-y-3">
						<div class="relative">
							<FormControl
								label="Card Number"
								type="text"
								placeholder="1234 5678 9012 3456"
								v-model="midtransCardDetails.card_number"
								@input="formatCardNumber"
								maxlength="19"
							/>
							<div v-if="detectedCardBrand" class="absolute right-3 top-7 flex items-center">
								<component :is="cardBrandIcon(detectedCardBrand)" />
							</div>
						</div>
						<div class="grid grid-cols-2 gap-3">
							<FormControl
								label="Expiry Month"
								type="text"
								placeholder="MM"
								v-model="midtransCardDetails.card_exp_month"
								maxlength="2"
							/>
							<FormControl
								label="Expiry Year"
								type="text"
								placeholder="YY"
								v-model="midtransCardDetails.card_exp_year"
								maxlength="2"
							/>
						</div>
						<FormControl
							label="CVV"
							type="text"
							placeholder="123"
							v-model="midtransCardDetails.card_cvv"
							maxlength="4"
						/>
					</div>
					<ErrorMessage class="mt-1" :message="cardErrorMessage" />
				</div>
				<FormControl
					class="mt-4"
					label="Name on Card"
					type="text"
					v-model="billingInformation.cardHolderName"
				/>
				<NewAddressForm
					ref="addressFormRef"
					class="mt-5"
					v-model="billingInformation"
					:disable-form="props.disableAddressForm"
					@success="console.log('Address form submitted')"
				/>
			</div>

			<div class="mt-3 space-y-4" v-show="tryingMicroCharge">
				<p class="text-base text-gray-700">
					We are attempting to charge your card with
					<strong>{{ formattedMicroChargeAmount }}</strong> to make sure the
					card works. This amount will be <strong>refunded</strong> back to your
					account.
				</p>
			</div>

			<div class="mt-3 space-y-4" v-show="processingMidtrans">
				<p class="text-base text-gray-700">
					Processing your card registration with Midtrans...
				</p>
			</div>

			<ErrorMessage class="mt-2" :message="errorMessage" />

			<div class="mt-6 flex items-center justify-between">
				<PoweredByStripeLogo v-if="paymentGateway === 'Stripe'" />
				<div v-else-if="paymentGateway === 'Midtrans'" class="flex items-center text-xs text-gray-500">
					Powered by <MidtransLogo class="h-7 w-24 ml-1" />
				</div>
				<Button
					v-if="showAddAnotherCardButton"
					label="Add Another Card"
					@click="clearForm"
				>
					<template #prefix>
						<FeatherIcon class="h-4" name="plus" />
					</template>
				</Button>
				<Button
					v-else-if="!tryingMicroCharge && !processingMidtrans"
					variant="solid"
					:label="'Verify & Save Card'"
					:loading="addingCard"
					@click="verifyWithMicroChargeIfApplicable"
				/>

				<Button
					v-else-if="tryingMicroCharge"
					:loading="!microChargeCompleted"
					:loadingText="'Verifying Card'"
				>
					Card Verified
					<template #prefix>
						<GreenCheckIcon class="h-4 w-4" />
					</template>
				</Button>

				<Button
					v-else-if="processingMidtrans"
					:loading="processingMidtrans"
					:loadingText="'Processing Card'"
				>
					Card Processing
				</Button>
			</div>
		</div>
	</div>
</template>
<script setup>
import NewAddressForm from './NewAddressForm.vue';
import PoweredByStripeLogo from '../../logo/PoweredByStripeLogo.vue';
import MidtransLogo from '../MidtransLogo.vue';
import {
	FeatherIcon,
	Button,
	FormControl,
	Spinner,
	ErrorMessage,
	createResource,
} from 'frappe-ui';
import { currency } from '../../utils/format';
import { cardBrandIcon } from '../../utils/components.jsx';
import { loadStripe } from '@stripe/stripe-js';
import { ref, reactive, computed, inject, onMounted } from 'vue';
import { toast } from 'vue-sonner';

const emit = defineEmits(['success']);
const props = defineProps({
	disableAddressForm: { type: Boolean, default: true },
});

const team = inject('team');

// Payment gateway variables
const paymentGateway = ref(null);
const gatewayConfig = ref(null);

// Stripe variables
const stripe = ref(null);
const elements = ref(null);
const card = ref(null);
const _setupIntent = ref(null);

// Midtrans variables
const midtransSnap = ref(null);
const processingMidtrans = ref(false);
const midtransCardDetails = reactive({
	card_number: '',
	card_exp_month: '',
	card_exp_year: '',
	card_cvv: ''
});

// Common variables
const ready = ref(false);
const errorMessage = ref(null);
const cardErrorMessage = ref(null);
const addingCard = ref(false);
const tryingMicroCharge = ref(false);
const showAddAnotherCardButton = ref(false);
const microChargeCompleted = ref(false);

onMounted(() => initializePaymentGateway());

const cardElementRef = ref(null);
const midtransCardElementRef = ref(null);

// Payment gateway configuration resource
const getPaymentGatewayConfig = createResource({
	url: 'press.api.billing.get_default_payment_gateway_config',
	onSuccess: async (data) => {
		console.log('DEBUG: Payment gateway config:', data);
		paymentGateway.value = data.gateway;
		gatewayConfig.value = data;
		
		if (data.gateway === 'Stripe') {
			await initializeStripe(data);
		} else if (data.gateway === 'Midtrans') {
			await initializeMidtrans(data);
		}
	},
	onError: (error) => {
		console.error('DEBUG: Failed to get payment gateway config:', error);
		errorMessage.value = 'Failed to initialize payment system. Please refresh the page.';
	}
});

const getPublishedKeyAndSetupIntent = createResource({
	url: 'press.api.billing.get_publishable_key_and_setup_intent',
	onSuccess: async (data) => {
		const { publishable_key, setup_intent } = data;
		_setupIntent.value = setup_intent;
		stripe.value = await loadStripe(publishable_key);
		elements.value = stripe.value.elements();
		const style = {
			base: {
				color: '#171717',
				fontFamily: [
					'ui-sans-serif',
					'system-ui',
					'-apple-system',
					'BlinkMacSystemFont',
					'"Segoe UI"',
					'Roboto',
					'"Helvetica Neue"',
					'Arial',
					'"Noto Sans"',
					'sans-serif',
					'"Apple Color Emoji"',
					'"Segoe UI Emoji"',
					'"Segoe UI Symbol"',
					'"Noto Color Emoji"',
				].join(', '),
				fontSmoothing: 'antialiased',
				fontSize: '13px',
				'::placeholder': {
					color: '#C7C7C7',
				},
			},
			invalid: {
				color: '#C7C7C7',
				iconColor: '#C7C7C7',
			},
		};
		card.value = elements.value.create('card', {
			hidePostalCode: true,
			style: style,
			classes: {
				complete: '',
				focus: 'bg-gray-100',
			},
		});
		card.value.mount(cardElementRef.value);
		card.value.addEventListener('change', (event) => {
			cardErrorMessage.value = event.error?.message || null;
		});
		card.value.addEventListener('ready', () => {
			ready.value = true;
		});
	},
});

const countryList = createResource({
	url: 'press.api.account.country_list',
	cache: 'countryList',
	auto: true,
});

const browserTimezone = computed(() => {
	if (!window.Intl) {
		return null;
	}
	return Intl.DateTimeFormat().resolvedOptions().timeZone;
});

const billingInformation = reactive({
	cardHolderName: '',
	country: '',
	gstin: '',
});

createResource({
	url: 'press.api.account.get_billing_information',
	params: { timezone: browserTimezone.value },
	auto: true,
	onSuccess: (data) => {
		billingInformation.country = data?.country;
		billingInformation.address = data?.address_line1;
		billingInformation.city = data?.city;
		billingInformation.state = data?.state;
		billingInformation.postal_code = data?.pincode;
		billingInformation.gstin =
			data?.gstin == 'Not Applicable' ? '' : data?.gstin;
	},
});

const setupIntentSuccess = createResource({
	url: 'press.api.billing.setup_intent_success',
	makeParams: ({ setupIntent }) => {
		console.log('DEBUG: setupIntentSuccess makeParams called');
		console.log('DEBUG: setupIntent for params:', setupIntent);
		console.log('DEBUG: billingInformation:', billingInformation);
		return {
			setup_intent: setupIntent,
			address: billingInformation,
		};
	},
	onSuccess: async ({ payment_method_name }) => {
		console.log('DEBUG: setupIntentSuccess onSuccess called');
		console.log('DEBUG: payment_method_name:', payment_method_name);
		addingCard.value = false;
		console.log('DEBUG: addingCard set to false');
		toast.success('Card added successfully');
		console.log('DEBUG: About to emit success');
		emit('success');
	},
	onError: (error) => {
		console.log('DEBUG: setupIntentSuccess onError called');
		console.error('DEBUG: Setup intent error:', error);
		addingCard.value = false;
		errorMessage.value = error.messages.join('\n');
		toast.error(errorMessage.value);
	},
});

const verifyCardWithMicroCharge = createResource({
	url: 'press.api.billing.create_payment_intent_for_micro_debit',
	onSuccess: async (paymentIntent) => {
		console.log('DEBUG: verifyCardWithMicroCharge onSuccess called');
		console.log('DEBUG: paymentIntent:', paymentIntent);
		
		let { client_secret } = paymentIntent;
		console.log('DEBUG: client_secret:', client_secret);

		console.log('DEBUG: About to call stripe.confirmCardPayment');
		let payload = await stripe.value.confirmCardPayment(client_secret, {
			payment_method: { card: card.value },
		});
		
		console.log('DEBUG: stripe.confirmCardPayment completed');
		console.log('DEBUG: payload:', payload);

		if (payload.paymentIntent?.status === 'succeeded') {
			console.log('DEBUG: Payment succeeded, setting microChargeCompleted to true');
			microChargeCompleted.value = true;
			console.log('DEBUG: About to call submit() from micro charge success');
			submit();
		} else {
			console.log('DEBUG: Payment not succeeded, error:', payload.error?.message);
			tryingMicroCharge.value = false;
			errorMessage.value = payload.error?.message;
		}
	},
	onError: (error) => {
		console.log('DEBUG: verifyCardWithMicroCharge onError called');
		console.error('DEBUG: Micro charge error:', error);
		tryingMicroCharge.value = false;
		errorMessage.value = error.messages.join('\n');
	},
});

// Midtrans card registration resource
const registerMidtransCard = createResource({
	url: 'press.api.billing.register_midtrans_card',
	onSuccess: async (response) => {
		console.log('DEBUG: Midtrans card registration response:', response);
		processingMidtrans.value = false;
		addingCard.value = false;
		
		if (response.success) {
			toast.success('Card registered successfully');
			emit('success');
		} else {
			console.error('DEBUG: Midtrans registration failed:', response);
			errorMessage.value = response.error ? response.error.join(', ') : 'Failed to register card';
		}
	},
	onError: (error) => {
		console.log('DEBUG: Midtrans card registration error:', error);
		processingMidtrans.value = false;
		addingCard.value = false;
		errorMessage.value = error.messages ? error.messages.join('\n') : 'Failed to register card';
	}
});


async function initializePaymentGateway() {
	console.log('DEBUG: Initializing payment gateway');
	await getPaymentGatewayConfig.submit();
}

async function initializeStripe(config) {
	console.log('DEBUG: Initializing Stripe with config:', config);
	_setupIntent.value = config.setup_intent;
	stripe.value = await loadStripe(config.publishable_key);
	elements.value = stripe.value.elements();
	
	const style = {
		base: {
			color: '#171717',
			fontFamily: [
				'ui-sans-serif',
				'system-ui',
				'-apple-system',
				'BlinkMacSystemFont',
				'"Segoe UI"',
				'Roboto',
				'"Helvetica Neue"',
				'Arial',
				'"Noto Sans"',
				'sans-serif',
				'"Apple Color Emoji"',
				'"Segoe UI Emoji"',
				'"Segoe UI Symbol"',
				'"Noto Color Emoji"',
			].join(', '),
			fontSmoothing: 'antialiased',
			fontSize: '13px',
			'::placeholder': {
				color: '#C7C7C7',
			},
		},
		invalid: {
			color: '#C7C7C7',
			iconColor: '#C7C7C7',
		},
	};
	
	card.value = elements.value.create('card', {
		hidePostalCode: true,
		style: style,
		classes: {
			complete: '',
			focus: 'bg-gray-100',
		},
	});
	
	card.value.mount(cardElementRef.value);
	card.value.addEventListener('change', (event) => {
		cardErrorMessage.value = event.error?.message || null;
	});
	card.value.addEventListener('ready', () => {
		ready.value = true;
	});

	// Set cardholder name from team info
	const { first_name, last_name = '' } = team.doc?.user_info;
	const fullname = `${first_name} ${last_name ?? ''}`;
	billingInformation.cardHolderName = fullname.trimEnd();
}

async function initializeMidtrans(config) {
	console.log('DEBUG: Initializing Midtrans with config:', config);
	
	try {
		if (!config.client_key) {
			throw new Error('Midtrans client key not provided');
		}
		
		// For custom card form, we don't need to load Snap script
		// Just set up the form
		
		// Set cardholder name from team info
		const { first_name, last_name = '' } = team.doc?.user_info;
		const fullname = `${first_name} ${last_name ?? ''}`;
		billingInformation.cardHolderName = fullname.trimEnd();
		
		ready.value = true;
		console.log('DEBUG: Midtrans initialization completed successfully');
	} catch (error) {
		console.error('DEBUG: Failed to initialize Midtrans:', error);
		errorMessage.value = `Failed to initialize payment system: ${error.message}`;
		ready.value = false;
	}
}

// Card brand detection
const detectedCardBrand = computed(() => {
	const cardNumber = midtransCardDetails.card_number.replace(/\D/g, '');
	return detectCardBrand(cardNumber);
});

function detectCardBrand(cardNumber) {
	// Remove spaces and non-digits
	const cleanNumber = cardNumber.replace(/\D/g, '');
	
	// Visa: starts with 4
	if (/^4/.test(cleanNumber)) {
		return 'visa';
	}
	
	// Mastercard: starts with 5[1-5] or 2[2-7]
	if (/^5[1-5]/.test(cleanNumber) || /^2[2-7]/.test(cleanNumber)) {
		return 'master-card';
	}
	
	// American Express: starts with 34 or 37
	if (/^3[47]/.test(cleanNumber)) {
		return 'amex';
	}
	
	// JCB: starts with 35
	if (/^35/.test(cleanNumber)) {
		return 'jcb';
	}
	
	// UnionPay: starts with 62 or 81
	if (/^62/.test(cleanNumber) || /^81/.test(cleanNumber)) {
		return 'union-pay';
	}
	
	// Default to generic if no match or too short
	return cleanNumber.length < 4 ? null : 'generic';
}

function formatCardNumber() {
	// Format card number with spaces (1234 5678 9012 3456)
	let value = midtransCardDetails.card_number.replace(/\D/g, '');
	value = value.replace(/(.{4})/g, '$1 ').trim();
	midtransCardDetails.card_number = value;
}


async function setupStripeIntent() {
	await getPublishedKeyAndSetupIntent.submit();
	const { first_name, last_name = '' } = team.doc?.user_info;
	const fullname = `${first_name} ${last_name ?? ''}`;
	billingInformation.cardHolderName = fullname.trimEnd();
}

const addressFormRef = ref(null);

async function submit() {
	console.log('DEBUG: submit() called');
	addingCard.value = true;
	console.log('DEBUG: addingCard set to true');
	
	console.log('DEBUG: About to validate address form');
	let message = await addressFormRef.value.validate();

	if (message) {
		console.log('DEBUG: Address validation failed:', message);
		errorMessage.value = message;
		addingCard.value = false;
		return;
	} else {
		console.log('DEBUG: Address validation passed');
		errorMessage.value = null;
	}

	console.log('DEBUG: About to call stripe.confirmCardSetup');
	console.log('DEBUG: setupIntent client_secret:', _setupIntent.value?.client_secret);
	
	const { setupIntent, error } = await stripe.value.confirmCardSetup(
		_setupIntent.value.client_secret,
		{
			payment_method: {
				card: card.value,
				billing_details: {
					name: billingInformation.cardHolderName,
					address: {
						line1: billingInformation.address,
						city: billingInformation.city,
						state: billingInformation.state,
						postal_code: billingInformation.postal_code,
						country: getCountryCode(team.doc?.country),
					},
				},
			},
		},
	);
	
	console.log('DEBUG: stripe.confirmCardSetup completed');
	console.log('DEBUG: setupIntent:', setupIntent);
	console.log('DEBUG: error:', error);
	
	if (error) {
		console.log('DEBUG: Processing stripe error');
		addingCard.value = false;
		let declineCode = error.decline_code;
		let _errorMessage = error.message;
		if (declineCode === 'do_not_honor') {
			errorMessage.value =
				"Your card was declined. It might be due to insufficient funds or you might've exceeded your daily limit. Please try with another card or contact your bank.";
			showAddAnotherCardButton.value = true;
		} else if (declineCode === 'transaction_not_allowed') {
			errorMessage.value =
				'Your card was declined. It might be due to restrictions on your card, like international transactions or online payments. Please try with another card or contact your bank.';
			showAddAnotherCardButton.value = true;
		} else if (_errorMessage != 'Your card number is incomplete.') {
			errorMessage.value = _errorMessage;
		}
	} else {
		console.log('DEBUG: No stripe error, checking setupIntent status');
		if (setupIntent?.status === 'succeeded') {
			console.log('DEBUG: setupIntent succeeded, calling setupIntentSuccess.submit');
			setupIntentSuccess.submit({ setupIntent });
		} else {
			console.log('DEBUG: setupIntent status is not succeeded:', setupIntent?.status);
		}
	}
}

async function verifyWithMicroChargeIfApplicable() {
	console.log('DEBUG: verifyWithMicroChargeIfApplicable called');
	console.log('DEBUG: addingCard state:', addingCard.value);
	console.log('DEBUG: paymentGateway:', paymentGateway.value);
	
	if (paymentGateway.value === 'Midtrans') {
		console.log('DEBUG: Using Midtrans flow');
		await processMidtransCardRegistration();
	} else if (paymentGateway.value === 'Stripe') {
		console.log('DEBUG: Using Stripe flow');
		const teamCurrency = team.doc?.currency;
		const verifyCardsWithMicroCharge = window.verify_cards_with_micro_charge;
		
		console.log('DEBUG: teamCurrency:', teamCurrency);
		console.log('DEBUG: verifyCardsWithMicroCharge:', verifyCardsWithMicroCharge);
		
		const isMicroChargeApplicable =
			verifyCardsWithMicroCharge === 'Both IDR and USD' ||
			(verifyCardsWithMicroCharge == 'Only IDR' && teamCurrency === 'IDR') ||
			(verifyCardsWithMicroCharge === 'Only USD' && teamCurrency === 'USD');
			
		console.log('DEBUG: isMicroChargeApplicable:', isMicroChargeApplicable);
		
		if (isMicroChargeApplicable) {
			console.log('DEBUG: Going to micro charge path');
			await _verifyWithMicroCharge();
		} else {
			console.log('DEBUG: Going to direct submit path');
			submit();
		}
	} else {
		errorMessage.value = 'Payment gateway not configured properly';
	}
}

async function _verifyWithMicroCharge() {
	console.log('DEBUG: _verifyWithMicroCharge called');
	tryingMicroCharge.value = true;
	console.log('DEBUG: tryingMicroCharge set to true');
	console.log('DEBUG: About to call verifyCardWithMicroCharge.submit()');
	return verifyCardWithMicroCharge.submit();
}

async function processMidtransCardRegistration() {
	console.log('DEBUG: processMidtransCardRegistration called with custom form');
	
	try {
		addingCard.value = true;
		processingMidtrans.value = true;
		
		// Validate address form first
		let message = await addressFormRef.value.validate();
		if (message) {
			console.log('DEBUG: Address validation failed:', message);
			errorMessage.value = message;
			addingCard.value = false;
			processingMidtrans.value = false;
			return;
		}
		
		// Validate card details
		if (!validateMidtransCardDetails()) {
			addingCard.value = false;
			processingMidtrans.value = false;
			return;
		}
		
		console.log('DEBUG: Card validation passed, registering card with Midtrans');
		
		// Call backend to register card with Midtrans
		await registerMidtransCard.submit({
			card_number: midtransCardDetails.card_number.replace(/\s/g, ''), // Remove spaces
			card_exp_month: midtransCardDetails.card_exp_month,
			card_exp_year: midtransCardDetails.card_exp_year,
			card_cvv: midtransCardDetails.card_cvv,
			card_holder_name: billingInformation.cardHolderName,
			brand: detectedCardBrand.value,
			billing_address: {
				address_line1: billingInformation.address,
				city: billingInformation.city,
				state: billingInformation.state,
				pincode: billingInformation.postal_code,
				country: billingInformation.country
			}
		});
		
	} catch (error) {
		console.error('DEBUG: Error in processMidtransCardRegistration:', error);
		processingMidtrans.value = false;
		addingCard.value = false;
		errorMessage.value = 'Failed to process card registration';
	}
}

function validateMidtransCardDetails() {
	console.log('DEBUG: Validating Midtrans card details');
	
	// Clear previous error
	cardErrorMessage.value = null;
	
	// Validate card number (basic check)
	const cardNumber = midtransCardDetails.card_number.replace(/\s/g, '');
	if (!cardNumber || cardNumber.length < 13 || cardNumber.length > 19) {
		cardErrorMessage.value = 'Please enter a valid card number';
		return false;
	}
	
	// Validate expiry month
	const month = parseInt(midtransCardDetails.card_exp_month);
	if (!month || month < 1 || month > 12) {
		cardErrorMessage.value = 'Please enter a valid expiry month (01-12)';
		return false;
	}
	
	// Validate expiry year
	const year = parseInt(midtransCardDetails.card_exp_year);
	const currentYear = new Date().getFullYear() % 100; // Get 2-digit year
	if (!year || year < currentYear) {
		cardErrorMessage.value = 'Please enter a valid expiry year';
		return false;
	}
	
	// Validate CVV
	const cvv = midtransCardDetails.card_cvv;
	if (!cvv || cvv.length < 3 || cvv.length > 4) {
		cardErrorMessage.value = 'Please enter a valid CVV';
		return false;
	}
	
	// Validate cardholder name
	if (!billingInformation.cardHolderName.trim()) {
		cardErrorMessage.value = 'Please enter the cardholder name';
		return false;
	}
	
	console.log('DEBUG: Card validation passed');
	return true;
}

function getCountryCode(country) {
	let code = countryList.data.find((d) => d.name === country).code;
	return code.toUpperCase();
}

async function clearForm() {
	ready.value = false;
	errorMessage.value = null;
	showAddAnotherCardButton.value = false;
	processingMidtrans.value = false;
	
	if (paymentGateway.value === 'Stripe') {
		card.value = null;
		await setupStripeIntent();
	} else if (paymentGateway.value === 'Midtrans') {
		// For Midtrans, just reset the ready state
		ready.value = true;
	}
}

const formattedMicroChargeAmount = computed(() => {
	if (!team.doc?.currency) {
		return 0;
	}
	return currency(
		team.doc?.billing_info?.micro_debit_charge_amount,
		team.doc?.currency,
	);
});
</script>