import re

import frappe
import razorpay
import stripe
from frappe.utils import fmt_money

from press.exceptions import CentralServerNotSet, FrappeioServerNotSet
from press.utils import get_current_team, log_error

states_with_tin = {
	"Andaman and Nicobar Islands": "35",
	"Andhra Pradesh": "37",
	"Arunachal Pradesh": "12",
	"Assam": "18",
	"Bihar": "10",
	"Chandigarh": "04",
	"Chhattisgarh": "22",
	"Dadra and Nagar Haveli and Daman and Diu": "26",
	"Delhi": "07",
	"Goa": "30",
	"Gujarat": "24",
	"Haryana": "06",
	"Himachal Pradesh": "02",
	"Jammu and Kashmir": "01",
	"Jharkhand": "20",
	"Karnataka": "29",
	"Kerala": "32",
	"Ladakh": "38",
	"Lakshadweep Islands": "31",
	"Madhya Pradesh": "23",
	"Maharashtra": "27",
	"Manipur": "14",
	"Meghalaya": "17",
	"Mizoram": "15",
	"Nagaland": "13",
	"Odisha": "21",
	"Other Territory": "97",
	"Puducherry": "34",
	"Punjab": "03",
	"Rajasthan": "08",
	"Sikkim": "11",
	"Tamil Nadu": "33",
	"Telangana": "36",
	"Tripura": "16",
	"Uttar Pradesh": "09",
	"Uttarakhand": "05",
	"West Bengal": "19",
}

GSTIN_FORMAT = re.compile("^[0-9]{2}[A-Z]{4}[0-9A-Z]{1}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}[1-9A-Z]{1}[0-9A-Z]{1}$")


def format_stripe_money(amount, currency):
	return fmt_money(amount / 100, 2, currency)


def get_erpnext_com_connection():
	from frappe.frappeclient import FrappeClient

	press_settings = frappe.get_single("Press Settings")
	erpnext_api_secret = press_settings.get_password("erpnext_api_secret", raise_exception=False)

	if not (press_settings.erpnext_api_key and press_settings.erpnext_url and erpnext_api_secret):
		frappe.throw("ERPNext.com URL not set up in Press Settings", exc=CentralServerNotSet)

	return FrappeClient(
		press_settings.erpnext_url,
		api_key=press_settings.erpnext_api_key,
		api_secret=erpnext_api_secret,
	)


def get_frappe_io_connection():
	if hasattr(frappe.local, "press_frappeio_conn"):
		return frappe.local.press_frappeio_conn

	from frappe.frappeclient import FrappeClient

	press_settings = frappe.get_single("Press Settings")
	frappe_api_key = press_settings.frappeio_api_key
	frappe_api_secret = press_settings.get_password("frappeio_api_secret", raise_exception=False)

	if not (frappe_api_key and frappe_api_secret and press_settings.frappe_url):
		frappe.throw("Frappe.io URL not set up in Press Settings", exc=FrappeioServerNotSet)

	frappe.local.press_frappeio_conn = FrappeClient(
		press_settings.frappe_url, api_key=frappe_api_key, api_secret=frappe_api_secret
	)

	return get_frappe_io_connection()


def is_frappe_auth_disabled():
	return frappe.db.get_single_value("Press Settings", "disable_frappe_auth", cache=True)


def make_formatted_doc(doc, fieldtypes=None):
	formatted = {}
	filters = None
	if fieldtypes:
		filters = {"fieldtype": ["in", fieldtypes]}

	for df in doc.meta.get("fields", filters):
		formatted[df.fieldname] = doc.get_formatted(df.fieldname)

	for tf in doc.meta.get_table_fields():
		formatted[tf.fieldname] = []
		for row in doc.get(tf.fieldname):
			formatted[tf.fieldname].append(make_formatted_doc(row))

	return formatted


def clear_setup_intent():
	team = get_current_team()
	frappe.cache().hdel("setup_intent", team)


def get_publishable_key():
	default_gateway = frappe.db.get_single_value("Press Settings", "default_payment_gateway") or "Midtrans"
	
	if default_gateway == "Stripe":
		return frappe.db.get_single_value("Press Settings", "stripe_publishable_key")
	elif default_gateway == "Midtrans":
		return get_midtrans_client_key()
	else:
		frappe.throw(f"Unsupported payment gateway: {default_gateway}")


def get_setup_intent(team):
	from frappe.utils import random_string

	default_gateway = frappe.db.get_single_value("Press Settings", "default_payment_gateway") or "Midtrans"
	
	if default_gateway == "Stripe":
		intent = frappe.cache().hget("setup_intent", team)
		if not intent:
			data = frappe.db.get_value("Team", team, ["stripe_customer_id", "currency"])
			customer_id = data[0]
			currency = data[1]
			stripe = get_stripe()
			hash = random_string(10)
			intent = stripe.SetupIntent.create(
				customer=customer_id,
				payment_method_types=["card"],
				payment_method_options={
					"card": {
						"request_three_d_secure": "automatic",
						"mandate_options": {
							"reference": f"Mandate-team:{team}-{hash}",
							"amount_type": "maximum",
							"amount": 1500000,
							"currency": currency.lower(),
							"start_date": int(frappe.utils.get_timestamp()),
							"interval": "sporadic",
							"supported_types": ["india"],
						},
					}
				},
			)
			frappe.cache().hset("setup_intent", team, intent)
		return intent
	
	elif default_gateway == "Midtrans":
		# For Midtrans, return client key for Snap.js integration
		return {
			"client_key": get_midtrans_client_key(),
			"sandbox": frappe.db.get_single_value("Press Settings", "midtrans_sandbox") or True
		}
	
	else:
		frappe.throw(f"Unsupported payment gateway: {default_gateway}")


def get_midtrans_snap_config(team):
	"""Get Midtrans Snap configuration for frontend integration"""
	default_gateway = frappe.db.get_single_value("Press Settings", "default_payment_gateway") or "Midtrans"
	
	if default_gateway != "Midtrans":
		frappe.throw("Midtrans Snap is only available when Midtrans is set as default payment gateway in Press Settings.")
	
	return {
		"client_key": get_midtrans_client_key(),
		"sandbox": frappe.db.get_single_value("Press Settings", "midtrans_sandbox") or True,
		"team": team
	}


def get_stripe():
	from frappe.utils.password import get_decrypted_password

	if not hasattr(frappe.local, "press_stripe_object"):
		secret_key = get_decrypted_password(
			"Press Settings",
			"Press Settings",
			"stripe_secret_key",
			raise_exception=False,
		)

		if not secret_key:
			frappe.throw("Setup stripe via Press Settings before using press.api.billing.get_stripe")

		stripe.api_key = secret_key
		# Set the maximum number of retries for network requests
		# https://docs.stripe.com/rate-limits?lang=python#object-lock-timeouts
		stripe.max_network_retries = 2
		frappe.local.press_stripe_object = stripe

	return frappe.local.press_stripe_object


def convert_stripe_money(amount):
	return (amount / 100) if amount else 0


def validate_gstin_check_digit(gstin, label="GSTIN"):
	"""Function to validate the check digit of the GSTIN."""
	factor = 1
	total = 0
	code_point_chars = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
	mod = len(code_point_chars)
	input_chars = gstin[:-1]
	for char in input_chars:
		digit = factor * code_point_chars.find(char)
		digit = (digit // mod) + (digit % mod)
		total += digit
		factor = 2 if factor == 1 else 1
	if gstin[-1] != code_point_chars[((mod - (total % mod)) % mod)]:
		frappe.throw(
			f"""Invalid {label}! The check digit validation has failed. Please ensure you've typed the {label} correctly."""
		)


def get_razorpay_client():
	from frappe.utils.password import get_decrypted_password

	if not hasattr(frappe.local, "press_razorpay_client_object"):
		key_id = frappe.db.get_single_value("Press Settings", "razorpay_key_id")
		key_secret = get_decrypted_password(
			"Press Settings", "Press Settings", "razorpay_key_secret", raise_exception=False
		)

		if not (key_id and key_secret):
			frappe.throw(
				"Setup razorpay via Press Settings before using press.api.billing.get_razorpay_client"
			)

		frappe.local.press_razorpay_client_object = razorpay.Client(auth=(key_id, key_secret))

	return frappe.local.press_razorpay_client_object


def process_micro_debit_test_charge(stripe_event):
	try:
		payment_intent = stripe_event["data"]["object"]
		metadata = payment_intent.get("metadata")
		payment_method_name = metadata.get("payment_method_name")

		frappe.db.set_value(
			"Stripe Payment Method", payment_method_name, "is_verified_with_micro_charge", True
		)

		frappe.get_doc(
			doctype="Stripe Micro Charge Record",
			stripe_payment_method=payment_method_name,
			stripe_payment_intent_id=payment_intent.get("id"),
		).insert(ignore_permissions=True)
	except Exception:
		log_error("Error Processing Stripe Micro Debit Charge", body=stripe_event)


def get_gateway_details(payment_record):
	partner_team = frappe.db.get_value("Mpesa Payment Record", payment_record, "payment_partner")
	return frappe.db.get_value(
		"Payment Gateway", {"team": partner_team}, ["gateway_controller", "print_format"]
	)


# Get partners external connection
def get_partner_external_connection(mpesa_setup):
	# check if connection is already established
	if hasattr(frappe.local, "_external_conn"):
		return frappe.local.press_external_conn

	from frappe.frappeclient import FrappeClient

	# Fetch API from gateway
	payment_gateway = frappe.get_all(
		"Payment Gateway",
		filters={"gateway_controller": mpesa_setup, "gateway_settings": "Mpesa Setup"},
		fields=["name", "url", "api_key", "api_secret"],
	)
	if not payment_gateway:
		frappe.throw("Mpesa Setup not set up in Payment Gateway")
	# Fetch API key and secret
	pg = frappe.get_doc("Payment Gateway", payment_gateway[0].name)
	api_key = pg.api_key
	api_secret = pg.get_password("api_secret")
	url = pg.url

	site_name = url.split("/api/method")[0]
	# Establish connection
	frappe.local._external_conn = FrappeClient(site_name, api_key=api_key, api_secret=api_secret)
	return frappe.local._external_conn


def get_midtrans():
	"""Get Midtrans configuration and return API details"""
	from frappe.utils.password import get_decrypted_password
	import base64

	if not hasattr(frappe.local, "press_midtrans_object"):
		server_key = get_decrypted_password(
			"Press Settings",
			"Press Settings", 
			"midtrans_server_key",
			raise_exception=False,
		)
		merchant_id = frappe.db.get_single_value("Press Settings", "midtrans_merchant_id")

		if not server_key:
			frappe.throw("Setup Midtrans via Press Settings before using press.api.billing.get_midtrans")

		# Create authorization header for Midtrans API
		auth_string = f"{server_key}:"
		auth_bytes = auth_string.encode("utf-8")
		auth_header = base64.b64encode(auth_bytes).decode("utf-8")

		# Get sandbox setting from Press Settings
		is_sandbox = frappe.db.get_single_value("Press Settings", "midtrans_sandbox") or True

		frappe.local.press_midtrans_object = {
			"server_key": server_key,
			"merchant_id": merchant_id,
			"auth_header": f"Basic {auth_header}",
			"sandbox_url": "https://api.sandbox.midtrans.com/v2",
			"production_url": "https://api.midtrans.com/v2",
			"snap_sandbox_url": "https://app.sandbox.midtrans.com/snap/v1/transactions",
			"snap_production_url": "https://app.midtrans.com/snap/v1/transactions",
			"is_sandbox": is_sandbox
		}

	return frappe.local.press_midtrans_object


def get_midtrans_client_key():
	"""Get Midtrans Client Key for frontend"""
	from frappe.utils.password import get_decrypted_password
	
	return get_decrypted_password(
		"Press Settings",
		"Press Settings",
		"midtrans_client_key",
		raise_exception=False,
	)


def create_midtrans_payment(order_id, amount, currency="IDR", customer_details=None):
	"""Create a payment transaction with Midtrans"""
	import requests
	
	midtrans = get_midtrans()
	url = f"{midtrans['sandbox_url'] if midtrans['is_sandbox'] else midtrans['production_url']}/charge"
	
	payload = {
		"payment_type": "credit_card",
		"transaction_details": {
			"order_id": order_id,
			"gross_amount": int(amount)
		},
		"credit_card": {
			"secure": True
		}
	}
	
	if customer_details:
		payload["customer_details"] = customer_details
	
	headers = {
		"Accept": "application/json",
		"Content-Type": "application/json",
		"Authorization": midtrans["auth_header"]
	}
	
	response = requests.post(url, json=payload, headers=headers)
	return response.json()


def verify_midtrans_notification(notification_json, signature_key):
	"""Verify Midtrans notification signature"""
	import hashlib
	
	midtrans = get_midtrans()
	
	# Create signature string
	order_id = notification_json.get("order_id")
	status_code = notification_json.get("status_code")
	gross_amount = notification_json.get("gross_amount")
	server_key = midtrans["server_key"]
	
	signature_string = f"{order_id}{status_code}{gross_amount}{server_key}"
	hashed = hashlib.sha512(signature_string.encode()).hexdigest()
	
	print(f"DEBUG:::signature_string: {signature_string}")
	print(f"DEBUG:::calculated_hash: {hashed}")
	print(f"DEBUG:::received_signature: {signature_key}")
	print(f"DEBUG:::signature_match: {hashed == signature_key}")
	
	return hashed == signature_key


def create_midtrans_snap_token(order_id, amount, currency="IDR", customer_details=None, item_details=None):
	"""Create Snap token for Midtrans payment UI"""
	import requests
	
	midtrans = get_midtrans()
	url = f"{midtrans['snap_sandbox_url'] if midtrans['is_sandbox'] else midtrans['snap_production_url']}"
	
	payload = {
		"transaction_details": {
			"order_id": order_id,
			"gross_amount": format_midtrans_money(amount, currency)
		}
	}
	
	if customer_details:
		payload["customer_details"] = customer_details
	
	if item_details:
		payload["item_details"] = item_details
	
	headers = {
		"Accept": "application/json",
		"Content-Type": "application/json", 
		"Authorization": midtrans["auth_header"]
	}
	
	response = requests.post(url, json=payload, headers=headers)
	return response.json()


def format_midtrans_money(amount, currency="IDR"):
	"""Format money for Midtrans (convert to smallest currency unit)"""
	# Midtrans expects amount in smallest currency unit (e.g., cents for USD, rupiah for IDR)
	if currency == "USD":
		return int(amount * 100)  # Convert to cents
	elif currency == "IDR":
		return int(amount)  # IDR is already in smallest unit
	else:
		return int(amount * 100)  # Default to cents
