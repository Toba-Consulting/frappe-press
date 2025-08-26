<template>
	<div class="relative">
		<div
			v-if="!ready"
			class="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-8 transform"
		>
			<Spinner class="h-5 w-5 text-gray-600" />
		</div>
		<div :class="{ 'opacity-0': !ready }">
			<div v-show="!processingPayment">
				<label class="block">
					<span class="block text-xs text-gray-600">
						Credit or Debit Card
					</span>
					<div
						class="form-input mt-2 block h-[unset] w-full py-2 pl-3"
						ref="card-element"
						id="card-element"
					></div>
					<ErrorMessage class="mt-1" :message="cardErrorMessage" />
				</label>
				<FormControl
					class="mt-4"
					label="Name on Card"
					type="text"
					v-model="billingInformation.cardHolderName"
				/>
				<AddressForm
					v-if="!withoutAddress"
					class="mt-4"
					v-model:address="billingInformation"
					ref="address-form"
				/>
			</div>

			<div class="mt-3" v-show="processingPayment">
				<p class="text-lg text-gray-800">
					Processing your payment with Midtrans...
				</p>
				<Button class="mt-2" :loading="true">Processing Payment</Button>
			</div>

			<ErrorMessage class="mt-2" :message="errorMessage" />

			<div class="mt-6 flex items-center justify-between">
				<MidtransLogo />
				<Button variant="solid" @click="submit" :loading="addingCard">
					Save Card
				</Button>
			</div>
		</div>
	</div>
</template>

<script>
import AddressForm from './AddressForm.vue';
import MidtransLogo from '@/components/MidtransLogo.vue';

export default {
	name: 'MidtransCard',
	props: ['withoutAddress'],
	emits: ['complete'],
	components: {
		AddressForm,
		MidtransLogo,
	},
	data() {
		return {
			errorMessage: null,
			cardErrorMessage: null,
			ready: false,
			midtransConfig: null,
			snap: null,
			billingInformation: {
				cardHolderName: '',
				country: '',
				address: '',
				city: '',
				state: '',
				postal_code: '',
				gstin: '',
			},
			addingCard: false,
			processingPayment: false,
		};
	},
	async mounted() {
		this.setupCard();

		let { first_name, last_name = '' } = this.$account.user;
		let fullname = first_name + ' ' + last_name;
		this.billingInformation.cardHolderName = fullname.trimEnd();
	},
	resources: {
		countryList: 'press.api.account.country_list',
		billingAddress() {
			return {
				url: 'press.api.billing.get_billing_information_gateway_agnostic',
				params: {
					timezone: this.browserTimezone,
				},
				auto: true,
				onSuccess(data) {
					this.billingInformation.country = data?.country;
					this.billingInformation.address = data?.address_line1;
					this.billingInformation.city = data?.city;
					this.billingInformation.state = data?.state;
					this.billingInformation.postal_code = data?.pincode;
				},
			};
		},
	},
	methods: {
		async setupCard() {
			try {
				// Get Midtrans client key and configuration
				let result = await this.$call(
					'press.api.billing.get_midtrans_client_key_and_config',
				);
				
				this.midtransConfig = result;
				
				if (!result.client_key) {
					throw new Error('Midtrans client key not configured');
				}

				// Load Midtrans Snap
				await this.loadMidtransSnap(result.client_key, result.is_sandbox);
				
				this.ready = true;
			} catch (error) {
				console.error('Failed to setup Midtrans:', error);
				this.errorMessage = 'Failed to initialize payment system';
			}
		},

		loadMidtransSnap(clientKey, isSandbox) {
			return new Promise((resolve, reject) => {
				const snapUrl = isSandbox 
					? 'https://app.sandbox.midtrans.com/snap/snap.js'
					: 'https://app.midtrans.com/snap/snap.js';

				// Check if script already loaded
				if (window.snap) {
					resolve();
					return;
				}

				const script = document.createElement('script');
				script.src = snapUrl;
				script.setAttribute('data-client-key', clientKey);
				script.onload = () => {
					this.snap = window.snap;
					resolve();
				};
				script.onerror = () => {
					reject(new Error('Failed to load Midtrans Snap'));
				};
				document.head.appendChild(script);
			});
		},

		async submit() {
			this.addingCard = true;
			this.errorMessage = null;

			// Validate address form if present
			let message;
			if (!this.withoutAddress) {
				message = await this.$refs['address-form'].validateValues();
			}
			if (message) {
				this.errorMessage = message;
				this.addingCard = false;
				return;
			}

			try {
				// For now, we'll create a test transaction to get card details
				// In a real implementation, you might use Midtrans' card registration
				const response = await this.$call(
					'press.api.billing.create_midtrans_snap_payment',
					{
						amount: 1000, // Small amount for card verification
						currency: this.$team.doc.currency === 'IDR' ? 'IDR' : 'USD',
					}
				);

				if (!response.success) {
					throw new Error(response.error?.[0] || 'Failed to create payment');
				}

				this.processingPayment = true;

				// Use Snap to get card token
				this.snap.pay(response.snap_token, {
					onSuccess: (result) => {
						this.handlePaymentSuccess(result);
					},
					onPending: (result) => {
						this.handlePaymentPending(result);
					},
					onError: (result) => {
						this.handlePaymentError(result);
					},
					onClose: () => {
						this.processingPayment = false;
						this.addingCard = false;
					}
				});

			} catch (error) {
				console.error('Payment setup failed:', error);
				this.errorMessage = error.message || 'Payment setup failed';
				this.addingCard = false;
			}
		},

		async handlePaymentSuccess(result) {
			try {
				// Extract card details from result
				const cardDetails = {
					name_on_card: this.billingInformation.cardHolderName,
					last_4: result.masked_card?.slice(-4) || '****',
					brand: result.card_type || 'unknown',
					card_type: 'credit', // Default, could be detected from result
					is_default: true
				};

				// Save payment method
				const saveResponse = await this.$call(
					'press.api.billing.save_midtrans_payment_method',
					{
						token: result.transaction_id,
						card_details: cardDetails,
						billing_address: this.withoutAddress ? null : this.billingInformation
					}
				);

				if (saveResponse.success) {
					this.$emit('complete', {
						payment_method_id: saveResponse.payment_method_id,
						is_default: saveResponse.is_default
					});
				} else {
					throw new Error(saveResponse.error?.[0] || 'Failed to save payment method');
				}

			} catch (error) {
				console.error('Failed to save payment method:', error);
				this.errorMessage = error.message || 'Failed to save payment method';
			} finally {
				this.processingPayment = false;
				this.addingCard = false;
			}
		},

		handlePaymentPending(result) {
			console.log('Payment pending:', result);
			this.errorMessage = 'Payment is pending. Please complete the payment process.';
			this.processingPayment = false;
			this.addingCard = false;
		},

		handlePaymentError(result) {
			console.error('Payment error:', result);
			this.errorMessage = result.status_message || 'Payment failed. Please try again.';
			this.processingPayment = false;
			this.addingCard = false;
		},

		getCountryCode(countryName) {
			if (!countryName) return '';
			const countryMap = {
				'Indonesia': 'ID',
				'United States': 'US',
				'Singapore': 'SG',
				'Malaysia': 'MY',
				'Thailand': 'TH',
				'Philippines': 'PH',
				'Vietnam': 'VN',
			};
			return countryMap[countryName] || countryName;
		},
	},
	computed: {
		browserTimezone() {
			return Intl.DateTimeFormat().resolvedOptions().timeZone;
		},
	},
};
</script>