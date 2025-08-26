/**
 * Payment utility functions for handling both Stripe and Midtrans
 */

// Payment gateway configuration
export const PAYMENT_GATEWAYS = {
	STRIPE: 'stripe',
	MIDTRANS: 'midtrans'
};

// Default payment gateway (can be configured via team settings)
let defaultPaymentGateway = PAYMENT_GATEWAYS.MIDTRANS; // Changed from Stripe to Midtrans

/**
 * Get the configured payment gateway for the team
 * @param {Object} team - Team object
 * @returns {string} Payment gateway identifier
 */
export function getPaymentGateway(team) {
	// Check if team has a specific payment gateway preference
	if (team?.payment_gateway) {
		return team.payment_gateway;
	}
	
	// Check if team currency suggests a specific gateway
	if (team?.currency === 'IDR') {
		return PAYMENT_GATEWAYS.MIDTRANS;
	} else if (team?.currency === 'USD') {
		// Could use either, but default to Midtrans for now
		return PAYMENT_GATEWAYS.MIDTRANS;
	}
	
	return defaultPaymentGateway;
}

/**
 * Set the default payment gateway
 * @param {string} gateway - Payment gateway identifier
 */
export function setDefaultPaymentGateway(gateway) {
	if (Object.values(PAYMENT_GATEWAYS).includes(gateway)) {
		defaultPaymentGateway = gateway;
	}
}

/**
 * Check if Midtrans is available for the given team
 * @param {Object} team - Team object
 * @returns {boolean}
 */
export function isMidtransAvailable(team) {
	// Midtrans is available for all teams, but typically used for IDR
	return true;
}

/**
 * Check if Stripe is available for the given team
 * @param {Object} team - Team object
 * @returns {boolean}
 */
export function isStripeAvailable(team) {
	// Stripe is available for all teams, but typically used for USD
	return true;
}

/**
 * Get the appropriate payment component based on gateway
 * @param {string} gateway - Payment gateway identifier
 * @param {string} componentType - Type of component (card, credits, etc.)
 * @returns {string} Component name
 */
export function getPaymentComponent(gateway, componentType = 'card') {
	const components = {
		[PAYMENT_GATEWAYS.STRIPE]: {
			card: 'StripeCard',
			cardDialog: 'StripeCardDialog',
			buyCredits: 'BuyCreditsStripe',
			logo: 'StripeLogo'
		},
		[PAYMENT_GATEWAYS.MIDTRANS]: {
			card: 'MidtransCard',
			cardDialog: 'MidtransCardDialog',
			buyCredits: 'BuyCreditsMidtrans',
			logo: 'MidtransLogo'
		}
	};
	
	return components[gateway]?.[componentType] || components[defaultPaymentGateway][componentType];
}

/**
 * Format currency for display based on gateway
 * @param {number} amount - Amount to format
 * @param {string} currency - Currency code
 * @param {string} gateway - Payment gateway
 * @returns {string} Formatted currency string
 */
export function formatCurrency(amount, currency = 'USD', gateway = defaultPaymentGateway) {
	const formatter = new Intl.NumberFormat('en-US', {
		style: 'currency',
		currency: currency,
		minimumFractionDigits: currency === 'IDR' ? 0 : 2,
		maximumFractionDigits: currency === 'IDR' ? 0 : 2,
	});
	
	return formatter.format(amount);
}

/**
 * Get minimum payment amount for the gateway/currency combination
 * @param {string} currency - Currency code
 * @param {string} gateway - Payment gateway
 * @returns {number} Minimum amount
 */
export function getMinimumPaymentAmount(currency = 'USD', gateway = defaultPaymentGateway) {
	const minimums = {
		[PAYMENT_GATEWAYS.STRIPE]: {
			'USD': 0.50,
			'IDR': 1000
		},
		[PAYMENT_GATEWAYS.MIDTRANS]: {
			'IDR': 1000,
			'USD': 1.00
		}
	};
	
	return minimums[gateway]?.[currency] || minimums[defaultPaymentGateway][currency] || 1.00;
}

/**
 * Convert amount to the payment gateway's expected format
 * @param {number} amount - Amount to convert
 * @param {string} currency - Currency code
 * @param {string} gateway - Payment gateway
 * @returns {number} Converted amount
 */
export function convertAmountForGateway(amount, currency = 'USD', gateway = defaultPaymentGateway) {
	// Stripe expects cents for USD, rupiah for IDR
	// Midtrans expects rupiah for IDR, cents for USD
	
	if (gateway === PAYMENT_GATEWAYS.STRIPE) {
		return currency === 'USD' ? Math.round(amount * 100) : Math.round(amount);
	} else if (gateway === PAYMENT_GATEWAYS.MIDTRANS) {
		return currency === 'IDR' ? Math.round(amount) : Math.round(amount * 100);
	}
	
	return Math.round(amount);
}

export default {
	PAYMENT_GATEWAYS,
	getPaymentGateway,
	setDefaultPaymentGateway,
	isMidtransAvailable,
	isStripeAvailable,
	getPaymentComponent,
	formatCurrency,
	getMinimumPaymentAmount,
	convertAmountForGateway
};