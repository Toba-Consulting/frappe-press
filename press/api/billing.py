# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and Contributors
# For license information, please see license.txt
from __future__ import annotations

from itertools import groupby

import frappe
from frappe import _  # Import this for translation functionality
from frappe.core.utils import find
from frappe.utils import fmt_money, get_request_site_address

from press.api.regional_payments.mpesa.utils import (
	create_invoice_partner_site,
	create_payment_partner_transaction,
	fetch_param_value,
	get_details_from_request_log,
	get_mpesa_setup_for_team,
	get_payment_gateway,
	sanitize_mobile_number,
	update_tax_id_or_phone_no,
)
from press.press.doctype.mpesa_setup.mpesa_connector import MpesaConnector
from press.press.doctype.team.team import (
	has_unsettled_invoices,
	_enqueue_finalize_unpaid_invoices_for_team,
)
from press.utils import get_current_team
from press.utils.billing import (
	GSTIN_FORMAT,
	clear_setup_intent,
	create_midtrans_payment,
	create_midtrans_snap_token,
	format_midtrans_money,
	get_midtrans,
	get_midtrans_client_key,
	get_publishable_key,
	get_razorpay_client,
	get_setup_intent,
	get_stripe,
	make_formatted_doc,
	states_with_tin,
	validate_gstin_check_digit,
)
from press.utils.mpesa_utils import create_mpesa_request_log

# from press.press.doctype.paymob_callback_log.paymob_callback_log import create_payment_partner_transaction


@frappe.whitelist()
def get_publishable_key_and_setup_intent():
	team = get_current_team()
	return {
		"publishable_key": get_publishable_key(),
		"setup_intent": get_setup_intent(team),
	}


@frappe.whitelist()
def get_midtrans_client_key_and_config():
	"""Get Midtrans client key and configuration for frontend"""
	is_sandbox = frappe.db.get_single_value("Press Settings", "midtrans_sandbox") or True
	return {
		"client_key": get_midtrans_client_key(),
		"is_sandbox": is_sandbox
	}


@frappe.whitelist()
def get_billing_information_gateway_agnostic(timezone=None):
	"""Get billing information without initializing any payment gateway"""
	from press.utils.country_timezone import get_country_from_timezone
	
	team = get_current_team()
	team_doc = frappe.get_doc("Team", team)
	
	billing_details = frappe._dict()
	if team_doc.billing_address:
		billing_details = frappe.get_doc("Address", team_doc.billing_address).as_dict()
		billing_details.billing_name = team_doc.billing_name

	if not billing_details.country and timezone:
		billing_details.country = get_country_from_timezone(timezone)

	return billing_details


@frappe.whitelist()
def get_payment_methods():
	"""Get payment methods for current team using default gateway"""
	default_gateway = frappe.db.get_single_value("Press Settings", "default_payment_gateway") or "Midtrans"
	
	if default_gateway == "Stripe":
		# Get Stripe payment methods (assuming this function exists)
		return frappe.call('press.api.billing.get_stripe_payment_methods')
	else:
		# Get Midtrans payment methods
		return get_midtrans_payment_methods()


@frappe.whitelist()
def create_payment_for_credits(amount, currency=None):
	"""Create payment for credits using default gateway"""
	team = get_current_team()
	team_doc = frappe.get_doc("Team", team)
	
	# Use team currency if not specified
	if not currency:
		currency = team_doc.currency
	
	default_gateway = frappe.db.get_single_value("Press Settings", "default_payment_gateway") or "Midtrans"
	
	if default_gateway == "Stripe":
		# Create Stripe payment (would need to implement this)
		return frappe.throw("Stripe credit payment not implemented yet")
	else:
		# Create Midtrans payment
		return create_midtrans_prepaid_credits(amount, currency)


@frappe.whitelist()
def create_payment_for_invoice(invoice_id):
	"""Create payment for invoice using default gateway"""
	default_gateway = frappe.db.get_single_value("Press Settings", "default_payment_gateway") or "Midtrans"
	
	if default_gateway == "Stripe":
		# Create Stripe invoice payment (would need to implement this)
		return frappe.throw("Stripe invoice payment not implemented yet")  
	else:
		# Create Midtrans invoice payment
		return pay_invoice_with_midtrans_snap(invoice_id)


@frappe.whitelist()
def get_default_payment_gateway_config():
	"""Get payment gateway configuration based on Press Settings"""
	default_gateway = frappe.db.get_single_value("Press Settings", "default_payment_gateway") or "Midtrans"
	
	if default_gateway == "Stripe":
		# Return Stripe configuration
		team = get_current_team()
		return {
			"gateway": "Stripe",
			"publishable_key": get_publishable_key(),
			"setup_intent": get_setup_intent(team),
		}
	else:
		# Return Midtrans configuration  
		is_sandbox = frappe.db.get_single_value("Press Settings", "midtrans_sandbox") or True
		return {
			"gateway": "Midtrans", 
			"client_key": get_midtrans_client_key(),
			"is_sandbox": is_sandbox
		}



@frappe.whitelist()
def create_midtrans_snap_payment(amount, currency="IDR", invoice_id=None, register_card=False):
	"""Create Midtrans Snap token for payment UI"""
	team = get_current_team()
	
	# Generate unique order ID
	order_id = f"{team}-{frappe.generate_hash(length=10)}"
	if invoice_id:
		order_id = f"inv-{invoice_id}-{frappe.generate_hash(length=6)}"
	
	# Format amount for Midtrans
	formatted_amount = format_midtrans_money(float(amount), currency)
	
	# Get team details for customer info
	team_doc = frappe.get_doc("Team", team)
	customer_details = {
		"first_name": team_doc.user,
		"email": team_doc.user,
		"phone": getattr(team_doc, 'phone', ''),
	}
	
	# Create item details
	item_details = [
		{
			"id": invoice_id or "credit_purchase",
			"price": formatted_amount,
			"quantity": 1,
			"name": f"Invoice {invoice_id}" if invoice_id else "Credit Purchase",
		}
	]
	
	try:
		response = create_midtrans_snap_token(
			order_id=order_id,
			amount=formatted_amount, 
			currency=currency,
			customer_details=customer_details,
			item_details=item_details
		)
		
		if "token" in response:
			return {
				"success": True,
				"snap_token": response["token"],
				"order_id": order_id,
				"redirect_url": response.get("redirect_url")
			}
		else:
			return {
				"success": False,
				"error": response.get("error_messages", ["Unknown error occurred"])
			}
			
	except Exception as e:
		frappe.log_error(f"Snap payment failed: {str(e)[:100]}", "Midtrans Error")
		return {
			"success": False,
			"error": ["Payment processing failed. Please try again."]
		}


@frappe.whitelist()
def create_midtrans_direct_payment(payment_method_id, amount, currency="IDR", invoice_id=None):
	"""Create direct payment using saved payment method"""
	team = get_current_team()
	
	# Validate payment method belongs to team
	payment_method = frappe.get_doc("Midtrans Payment Method", payment_method_id)
	if payment_method.team != team:
		frappe.throw("Invalid payment method")
	
	# Generate unique order ID
	order_id = f"{team}-{frappe.generate_hash(length=10)}"
	if invoice_id:
		order_id = f"inv-{invoice_id}-{frappe.generate_hash(length=6)}"
	
	try:
		response = create_midtrans_payment(
			order_id=order_id,
			amount=format_midtrans_money(float(amount), currency),
			currency=currency
		)
		
		# Payment event will be created when webhook is received from Midtrans
		# Do not create payment event here to avoid duplicates
		
		return {
			"success": True,
			"transaction_id": response.get("transaction_id"),
			"status": response.get("transaction_status"),
			"order_id": order_id
		}
		
	except Exception as e:
		frappe.log_error(f"Direct payment failed: {str(e)[:100]}", "Midtrans Error")
		return {
			"success": False,
			"error": ["Payment processing failed. Please try again."]
		}


@frappe.whitelist()
def get_midtrans_payment_methods():
	"""Get all Midtrans payment methods for current team"""
	from press.press.doctype.midtrans_payment_method.midtrans_payment_method import get_payment_methods
	team = get_current_team()
	
	# Add debugging
	frappe.log_error("Get Payment Methods", f"Called for team: {team}")
	
	methods = get_payment_methods()
	frappe.log_error("Payment Methods Result", f"Found {len(methods)} methods: {methods}")
	
	return methods


@frappe.whitelist()
def register_midtrans_card(card_number, card_exp_month, card_exp_year, card_cvv, card_holder_name, brand=None, billing_address=None):
	"""Register a card directly with Midtrans using card tokenization"""
	team = get_current_team()
	
	try:
		frappe.log_error("Card Registration Start", f"Team: {team}")
		
		# Call Midtrans tokenization API
		token_response = create_midtrans_card_token(
			card_number=card_number,
			card_exp_month=card_exp_month,
			card_exp_year=card_exp_year,
			card_cvv=card_cvv,
			card_holder_name=card_holder_name
		)
		
		frappe.log_error("Token Response", str(token_response))
		
		if not token_response.get("success"):
			return {
				"success": False,
				"error": token_response.get("error", ["Failed to tokenize card"])
			}
		
		# Extract card details and token
		card_token = token_response["token_id"]
		card_details = token_response.get("card_details", {})
		
		frappe.log_error("Card Token", f"Token: {card_token[:20]}... Details: {card_details}")
		
		# Save the card token to our database
		frappe.log_error("Creating Payment Method", "Starting document creation")
		
		# Ensure field lengths are within limits and valid values
		name_on_card = (card_holder_name or "")[:140]  # Data field default length
		
		# Extract last_4 from card_details or card_number
		if "last_4" in card_details:
			last_4 = str(card_details["last_4"])[:4]
		else:
			# Extract from card_number if not in card_details
			last_4 = str(card_number)[-4:]
			
		expiry_month = str(card_exp_month).zfill(2)[:2]  # 2-digit format for database
		expiry_year = str(card_exp_year).zfill(2)[:2]    # 2-digit format for database (YY)
		
		# Use frontend-detected brand if provided, otherwise use Midtrans brand
		if brand:
			brand = str(brand)[:140]  # Use the frontend-detected brand
		else:
			brand = str(card_details.get("brand", "Unknown"))[:140]  # Fall back to Midtrans brand
		
		# card_type must be exactly 'credit' or 'debit' as per DocType definition
		raw_card_type = str(card_details.get("card_type", "credit")).lower()
		if raw_card_type in ["debit"]:
			card_type = "debit"
		else:
			card_type = "credit"  # Default to credit
			
		token = str(card_token)[:140]  # Data field default length
		
		frappe.log_error("Field Values", f"name: {name_on_card}, last_4: {last_4}, month: {expiry_month}, year: {expiry_year}, brand: {brand}, type: {card_type}")
		
		payment_method = frappe.get_doc({
			"doctype": "Midtrans Payment Method",
			"team": team,
			"name_on_card": name_on_card,
			"last_4": last_4,
			"expiry_month": expiry_month,
			"expiry_year": expiry_year,
			"brand": brand,
			"card_type": card_type,
			"midtrans_token": token,
			"is_default": 0
		})
		
		# Insert the payment method first to get the name
		frappe.log_error("Database Insert", "About to insert payment method")
		try:
			payment_method.insert(ignore_permissions=True)
			frappe.log_error("Insert Success", f"Name: {payment_method.name}")
			
			# If this is the first payment method for the team, set it as default in Team doctype
			existing_methods = frappe.db.count("Midtrans Payment Method", {"team": team})
			if existing_methods == 1:  # This is the first card
				team_doc = frappe.get_doc("Team", team)
				team_doc.default_payment_method = payment_method.name
				team_doc.save(ignore_permissions=True)
				frappe.log_error("Team Default Set", f"Set {payment_method.name} as default for team {team}")
			
			# Commit the transaction to ensure it's saved
			frappe.db.commit()
			
			# Verify it was saved by querying it back
			saved_method = frappe.get_doc("Midtrans Payment Method", payment_method.name)
			frappe.log_error("Verification", f"Saved payment method: {saved_method.name}, Team: {saved_method.team}, Last 4: {saved_method.last_4}")
			
		except Exception as insert_error:
			frappe.log_error("Insert Failed", str(insert_error))
			raise
		
		# Only create billing address if team doesn't already have one
		team_doc = frappe.get_doc("Team", team)
		
		if billing_address and not team_doc.billing_address:
			frappe.log_error("Creating Address", "Creating billing address for first payment method")
			# Create address after payment method is saved and has a name
			address_doc = frappe.get_doc({
				"doctype": "Address",
				"address_title": f"{team} Billing Address",
				"address_type": "Billing",
				"address_line1": billing_address.get("address_line1"),
				"address_line2": billing_address.get("address_line2"),
				"city": billing_address.get("city"),
				"state": billing_address.get("state"),
				"pincode": billing_address.get("pincode"),
				"country": billing_address.get("country"),
			})
			address_doc.append("links", {
				"link_doctype": "Midtrans Payment Method",
				"link_name": payment_method.name  # Now payment_method.name exists
			})
			address_doc.insert(ignore_permissions=True)
			
			# Update team's billing_address field
			team_doc.billing_address = address_doc.name
			team_doc.save(ignore_permissions=True)
		elif billing_address and team_doc.billing_address:
			frappe.log_error("Skip Address Creation", f"Skipping address creation - team already has billing address: {team_doc.billing_address}")
		
		team_doc.country = billing_address.get("country")
		team_doc.payment_method = "Card"
		team_doc.save(ignore_permissions=True)

		return {
			"success": True,
			"payment_method_id": payment_method.name,
			"is_default": payment_method.is_default
		}
		
	except Exception as e:
		frappe.log_error(f"Card register failed: {str(e)[:100]}", "Midtrans Error")
		return {
			"success": False,
			"error": [f"Failed to register card: {str(e)}"]
		}


def create_midtrans_card_token(card_number, card_exp_month, card_exp_year, card_cvv=None, card_holder_name=None):
	"""Create card token using Midtrans Card Registration API"""
	import requests
	import base64
	
	try:
		midtrans = get_midtrans()
		client_key = get_midtrans_client_key()
		
		if not client_key:
			return {
				"success": False,
				"error": ["Midtrans client key not configured"]
			}
		
		# Create authorization header with client_key + ":" encoded in base64
		auth_string = f"{client_key}:"
		auth_bytes = auth_string.encode("utf-8")
		auth_header = f"Basic {base64.b64encode(auth_bytes).decode('utf-8')}"
		
		# Use correct Midtrans card registration endpoint
		base_url = "https://api.sandbox.midtrans.com" if midtrans['is_sandbox'] else "https://api.midtrans.com"
		url = f"{base_url}/v2/card/register"
		
		# Parameters for GET request as per Midtrans docs
		# Convert YY to YYYY format for card_exp_year as required by Midtrans
		year_str = str(card_exp_year).zfill(2)
		if len(year_str) == 2:
			# Convert YY to YYYY (e.g., "26" becomes "2026", "05" becomes "2005" but should be "2025")
			year_int = int(year_str)
			current_year = 2025  # Current year for reference
			
			# If year is less than current year's last 2 digits, assume next century
			# Otherwise assume current century
			if year_int < (current_year % 100):
				full_year = 2100 + year_int  # Next century
			else:
				full_year = 2000 + year_int  # Current century
		else:
			# Already 4-digit year
			full_year = int(year_str)
			
		params = {
			"card_number": card_number,
			"card_exp_month": str(card_exp_month).zfill(2),  # Ensure 2-digit format (MM)
			"card_exp_year": str(full_year),  # Ensure 4-digit format (YYYY)
			"client_key": client_key  # Include client_key in parameters as well
		}
		
		print(f"DEBUG:::: params sent {params}")

		# Headers with proper authorization
		headers = {
			"Accept": "application/json",
			"Authorization": auth_header,
			"Content-Type": "application/json"
		}
		
		frappe.log_error(f"API Call: {url}", "Midtrans Debug")
		
		# Use GET method as per Midtrans documentation
		response = requests.get(url, params=params, headers=headers)
		
		frappe.log_error(f"Status: {response.status_code}", "Midtrans Response")
		
		result = response.json()
		
		print(f"DEBUG :::: response result {result}")

		if response.status_code == 200 and "saved_token_id" in result:
			# Extract card details from Midtrans response
			masked_card = result.get("masked_card", "")
			
			return {
				"success": True,
				"token_id": result["saved_token_id"],
				"card_details": {
					"last_4": masked_card[-4:] if masked_card else card_number[-4:],
					"brand": result.get("card_type", "Unknown"),
					"card_type": "credit",  # Default to credit
					"masked_card": masked_card,
					"transaction_id": result.get("transaction_id", "")
				}
			}
		else:
			frappe.log_error("Midtrans Registration Failed", str(result))
			return {
				"success": False,
				"error": [result.get("error_messages", [result.get("error_message", "Card registration failed")])]
			}
			
	except Exception as e:
		frappe.log_error("Midtrans API Error", str(e))
		return {
			"success": False,
			"error": [f"Card registration failed: {str(e)}"]
		}


@frappe.whitelist()
def save_midtrans_payment_method(token, card_details, billing_address=None):
	"""Save a new Midtrans payment method"""
	team = get_current_team()
	
	try:
		# Create payment method record
		payment_method = frappe.get_doc({
			"doctype": "Midtrans Payment Method",
			"team": team,
			"name_on_card": card_details.get("name_on_card"),
			"last_4": card_details.get("last_4"),
			"expiry_month": card_details.get("expiry_month"),
			"expiry_year": card_details.get("expiry_year"),
			"brand": card_details.get("brand"),
			"card_type": card_details.get("card_type", "credit"),
			"midtrans_token": token,
			"is_default": card_details.get("is_default", False)
		})
		
		if billing_address:
			# Create address if provided
			address_doc = frappe.get_doc({
				"doctype": "Address",
				"address_title": f"{team} Billing Address",
				"address_type": "Billing",
				"address_line1": billing_address.get("address_line1"),
				"address_line2": billing_address.get("address_line2"),
				"city": billing_address.get("city"),
				"state": billing_address.get("state"),
				"pincode": billing_address.get("pincode"),
				"country": billing_address.get("country"),
			})
			address_doc.append("links", {
				"link_doctype": "Midtrans Payment Method",
				"link_name": payment_method.name
			})
			address_doc.insert(ignore_permissions=True)
			
		payment_method.insert(ignore_permissions=True)
		
		return {
			"success": True,
			"payment_method_id": payment_method.name,
			"is_default": payment_method.is_default
		}
		
	except Exception as e:
		frappe.log_error(f"Save method failed: {str(e)[:100]}", "Midtrans Error")
		return {
			"success": False,
			"error": ["Failed to save payment method. Please try again."]
		}


@frappe.whitelist()
def set_default_midtrans_payment_method(payment_method_id):
	"""Set a Midtrans payment method as default"""
	team = get_current_team()
	
	# Validate payment method belongs to team
	payment_method = frappe.get_doc("Midtrans Payment Method", payment_method_id)
	if payment_method.team != team:
		frappe.throw("Invalid payment method")
	
	try:
		# Update all payment methods for team to non-default
		frappe.db.sql(
			"""UPDATE `tabMidtrans Payment Method` 
			   SET is_default = 0 
			   WHERE team = %s""",
			[team]
		)
		
		# Set this one as default
		payment_method.is_default = 1
		payment_method.save(ignore_permissions=True)
		
		return {"success": True}
		
	except Exception as e:
		frappe.log_error(f"Set default failed: {str(e)[:100]}", "Midtrans Error")
		return {
			"success": False,
			"error": ["Failed to update payment method. Please try again."]
		}


@frappe.whitelist()
def delete_midtrans_payment_method(payment_method_id):
	"""Delete a Midtrans payment method"""
	team = get_current_team()
	
	# Validate payment method belongs to team
	payment_method = frappe.get_doc("Midtrans Payment Method", payment_method_id)
	if payment_method.team != team:
		frappe.throw("Invalid payment method")
	
	try:
		return payment_method.delete()
	except Exception as e:
		frappe.log_error(f"Delete method failed: {str(e)[:100]}", "Midtrans Error")
		return {
			"success": False,
			"error": ["Failed to delete payment method. Please try again."]
		}


@frappe.whitelist()
def pay_invoice_with_midtrans_snap(invoice_id):
	"""Create Snap payment for a specific invoice"""
	team = get_current_team()
	
	# Validate invoice exists and belongs to team
	invoice = frappe.get_doc("Invoice", invoice_id)
	if invoice.team != team:
		frappe.throw("Invalid invoice")
	
	if invoice.status == "Paid":
		return {
			"success": False,
			"error": ["Invoice is already paid"]
		}
	
	# Use the existing snap payment endpoint
	return create_midtrans_snap_payment(
		amount=invoice.amount_due,
		currency=invoice.currency,
		invoice_id=invoice_id
	)


@frappe.whitelist()
def pay_invoice_with_midtrans_method(invoice_id, payment_method_id):
	"""Pay invoice using saved Midtrans payment method"""
	team = get_current_team()
	
	# Validate invoice exists and belongs to team
	invoice = frappe.get_doc("Invoice", invoice_id)
	if invoice.team != team:
		frappe.throw("Invalid invoice")
	
	if invoice.status == "Paid":
		return {
			"success": False,
			"error": ["Invoice is already paid"]
		}
	
	# Use the existing direct payment endpoint
	response = create_midtrans_direct_payment(
		payment_method_id=payment_method_id,
		amount=invoice.amount_due,
		currency=invoice.currency,
		invoice_id=invoice_id
	)
	
	# Update invoice status if payment successful
	if response.get("success") and response.get("status") in ["capture", "settle"]:
		try:
			invoice.status = "Paid"
			invoice.save(ignore_permissions=True)
			frappe.db.commit()
		except Exception as e:
			frappe.log_error(f"Failed to update invoice status: {str(e)}")
	
	return response


@frappe.whitelist()
def create_midtrans_prepaid_credits(amount, currency="IDR"):
	"""Create Snap payment for prepaid credits"""
	team = get_current_team()
	
	if float(amount) < 1:
		return {
			"success": False,
			"error": ["Minimum amount is 1.00"]
		}
	
	# Create Snap token for prepaid credits
	return create_midtrans_snap_payment(
		amount=amount,
		currency=currency,
		invoice_id=None  # No specific invoice, this is for credits
	)


@frappe.whitelist()
def verify_midtrans_payment_status(order_id, transaction_id=None):
	"""Verify payment status from Midtrans"""
	import requests
	
	try:
		midtrans = get_midtrans()
		
		# Use transaction_id if provided, otherwise use order_id
		payment_id = transaction_id or order_id
		url = f"{midtrans['sandbox_url'] if midtrans['is_sandbox'] else midtrans['production_url']}/{payment_id}/status"
		
		headers = {
			"Accept": "application/json",
			"Authorization": midtrans["auth_header"]
		}
		
		response = requests.get(url, headers=headers)
		payment_data = response.json()
		
		# Update payment event if exists
		if payment_data.get("transaction_status"):
			payment_event = frappe.db.get_value(
				"Midtrans Payment Event", 
				{"midtrans_order_id": order_id}, 
				"name"
			)
			
			if payment_event:
				event_doc = frappe.get_doc("Midtrans Payment Event", payment_event)
				event_doc.transaction_status = payment_data.get("transaction_status")
				event_doc.midtrans_transaction_object = frappe.as_json(payment_data)
				event_doc.save(ignore_permissions=True)
				event_doc.map_transaction_status_to_payment_status()
				event_doc.save(ignore_permissions=True)
		
		return {
			"success": True,
			"status": payment_data.get("transaction_status"),
			"payment_data": payment_data
		}
		
	except Exception as e:
		frappe.log_error(f"Verify status failed: {str(e)[:100]}", "Midtrans Error")
		return {
			"success": False,
			"error": ["Failed to verify payment status"]
		}


def get_bank_display_name(bank_code):
	"""Get human-readable bank name from bank code"""
	bank_names = {
		"bca": "Bank Central Asia (BCA)",
		"bni": "Bank Negara Indonesia (BNI)",
		"bri": "Bank Rakyat Indonesia (BRI)",
		"mandiri": "Bank Mandiri",
		"permata": "Bank Permata",
		"cimb": "CIMB Niaga",
		"other": "Other Bank"
	}
	return bank_names.get(bank_code.lower(), bank_code.upper())


def get_bank_instructions(bank_code):
	"""Get bank-specific payment instructions"""
	instructions = {
		"bca": [
			"Login to your BCA mobile banking or internet banking",
			"Select \"Transfer\" menu",
			"Choose \"Virtual Account\" as destination",
			"Enter the Virtual Account Number",
			"Enter the exact amount",
			"Confirm and complete the transfer"
		],
		"bni": [
			"Login to your BNI mobile banking or internet banking",
			"Select \"Transfer\" menu",
			"Choose \"Virtual Account Billing\" as destination",
			"Enter the Virtual Account Number",
			"Enter the exact amount",
			"Confirm and complete the transfer"
		],
		"bri": [
			"Login to your BRI mobile banking or internet banking",
			"Select \"Transfer\" menu",
			"Choose \"BRIVA\" as destination",
			"Enter the Virtual Account Number",
			"Enter the exact amount",
			"Confirm and complete the transfer"
		],
		"mandiri": [
			"Login to your Mandiri mobile banking or internet banking",
			"Select \"Transfer\" menu",
			"Choose \"Virtual Account\" as destination",
			"Enter the Virtual Account Number",
			"Enter the exact amount",
			"Confirm and complete the transfer"
		],
		"permata": [
			"Login to your Permata mobile banking or internet banking",
			"Select \"Transfer\" menu",
			"Choose \"Virtual Account\" as destination",
			"Enter the Virtual Account Number",
			"Enter the exact amount",
			"Confirm and complete the transfer"
		],
		"cimb": [
			"Login to your CIMB Niaga mobile banking or internet banking",
			"Select \"Transfer\" menu",
			"Choose \"Virtual Account\" as destination",
			"Enter the Virtual Account Number",
			"Enter the exact amount",
			"Confirm and complete the transfer"
		]
	}
	return instructions.get(bank_code.lower(), instructions["bca"])


@frappe.whitelist()
def get_bank_payment_instructions(bank_code):
	"""Get payment instructions for a specific bank"""
	return {
		"bank_code": bank_code.upper(),
		"bank_name": get_bank_display_name(bank_code),
		"instructions": get_bank_instructions(bank_code)
	}


@frappe.whitelist()
def create_midtrans_ewallet_payment(amount, currency="IDR", ewallet="gopay"):
	"""Create E-Wallet payment using Midtrans Core API"""
	team = get_current_team()
	
	if float(amount) < 1:
		return {
			"success": False,
			"error": "Minimum amount is 1.00"
		}
	
	try:
		# Get Midtrans configuration from Press Settings
		press_settings = frappe.get_single("Press Settings")
		is_sandbox = press_settings.midtrans_sandbox
		server_key = press_settings.get_password("midtrans_server_key")
		
		if not server_key:
			return {
				"success": False,
				"error": "Midtrans server key not configured in Press Settings"
			}

		import requests
		import json
		from datetime import datetime
		
		# Generate unique order ID (Midtrans requirements: max 50 chars, alphanumeric + dash/underscore only)
		doc_team = frappe.get_doc("Team", team)
		current_time = datetime.now()
		formatted_current_time = current_time.strftime("%d%m%Y%H%M%S")
		order_id = f"CREDITS-{doc_team.user}-{formatted_current_time}"

		# Prepare request data for E-Wallet Core API
		# Different E-Wallets have different payment types and structures
		if ewallet.lower() == 'gopay':
			request_data = {
				"payment_type": "gopay",
				"transaction_details": {
					"order_id": order_id,
					"gross_amount": int(float(amount))
				},
				"gopay": {
					"enable_callback": True,
					"callback_url": get_request_site_address(True) + "/api/method/press.api.billing.verify_midtrans_ewallet_payment"
				}
			}
		elif ewallet.lower() == 'qris':
			request_data = {
				"payment_type": "qris",
				"transaction_details": {
					"order_id": order_id,
					"gross_amount": int(float(amount))
				}
			}
		elif ewallet.lower() in ['ovo', 'dana', 'shopeepay']:
			# For OVO, DANA, ShopeePay - use ewallet payment type
			request_data = {
				"payment_type": "ewallet",
				"transaction_details": {
					"order_id": order_id,
					"gross_amount": int(float(amount))
				},
				"ewallet": {
					"channel": ewallet.lower()
				}
			}
		else:
			return {
				"success": False,
				"error": f"Unsupported E-Wallet provider: {ewallet}"
			}
		
		# Prepare authorization header (Base64 encode server_key + ":")
		auth_string = f"{server_key}:"
		import base64
		auth_header = base64.b64encode(auth_string.encode()).decode()
		
		headers = {
			"Accept": "application/json",
			"Content-Type": "application/json",
			"Authorization": f"Basic {auth_header}"
		}
		
		# Use appropriate API URL based on sandbox/production mode
		base_url = "https://api.sandbox.midtrans.com/v2" if is_sandbox else "https://api.midtrans.com/v2"
		url = f"{base_url}/charge"
		
		response = requests.post(url, headers=headers, data=json.dumps(request_data))
		
		if response.status_code == 200:
			payment_data = response.json()
			
			# Check if payment was created successfully using response status_code
			if payment_data.get("status_code") == "201":
				# Extract payment information based on E-Wallet type
				payment_info = {}
				
				# Extract payment information based on E-Wallet type
				actions = payment_data.get('actions', [])
				
				if ewallet.lower() == 'gopay':
					# GoPay usually has: [0] = QR code, [1] = deeplink
					qr_code = None
					deeplink = None
					
					for action in actions:
						if action.get('method') == 'GET':  # QR code
							qr_code = action.get('url')
						elif action.get('method') == 'POST':  # Deeplink  
							deeplink = action.get('url')
					
					# Fallback: if no method specified, assume first is QR, second is deeplink
					if not qr_code and actions:
						qr_code = actions[0].get('url')
					if not deeplink and len(actions) > 1:
						deeplink = actions[1].get('url')
					
					payment_info = {
						"qr_code": qr_code,
						"deeplink": deeplink
					}
					
				elif ewallet.lower() == 'qris':
					# QRIS only has QR code
					payment_info = {
						"qr_code": actions[0].get('url') if actions else None,
						"deeplink": None  # QRIS doesn't have deeplink
					}
					
				elif ewallet.lower() in ['ovo', 'dana', 'shopeepay']:
					# These wallets usually provide deeplink only
					payment_info = {
						"qr_code": None,
						"deeplink": actions[0].get('url') if actions else None
					}
				else:
					# Fallback for unknown wallets
					payment_info = {
						"qr_code": actions[0].get('url') if actions else None,
						"deeplink": actions[1].get('url') if len(actions) > 1 else None
					}
				
				# Payment event will be created when webhook is received from Midtrans
				# Do not create payment event here to avoid duplicates
				
				return {
					"success": True,
					"data": {
						"transaction_id": payment_data.get("transaction_id"),
						"order_id": order_id,
						"status": payment_data.get("transaction_status"),
						"amount": float(amount),
						"currency": currency,
						"ewallet": ewallet.upper(),
						"ewallet_name": get_ewallet_display_name(ewallet),
						"payment_type": "ewallet",
						"expiry_time": payment_data.get("expiry_time"),
						**payment_info
					}
				}
			else:
				# Payment creation failed, return error from response
				error_messages = payment_data.get("error_messages", [])
				status_message = payment_data.get("status_message", "")
				
				if not error_messages and status_message:
					error_messages = [status_message]
				elif not error_messages:
					error_messages = [f"Payment creation failed with status {payment_data.get('status_code')}"]
				
				return {
					"success": False,
					"error": error_messages[0] if len(error_messages) == 1 else error_messages,
					"status_code": payment_data.get("status_code"),
					"raw_response": response.text[:500]
				}
		else:
			# Enhanced error handling
			error_data = {}
			try:
				error_data = response.json() if response.content else {}
			except:
				pass
				
			frappe.log_error(f"E-Wallet payment failed: {response.text[:100]}", "Midtrans Error")
			
			# Return more detailed error information
			error_messages = error_data.get("error_messages", [])
			status_message = error_data.get("status_message", "")
			
			if not error_messages and status_message:
				error_messages = [status_message]
			elif not error_messages:
				error_messages = [f"API request failed with status {response.status_code}"]
			
			return {
				"success": False,
				"error": error_messages[0] if len(error_messages) == 1 else error_messages,
				"status_code": response.status_code,
				"raw_response": response.text[:500]
			}
			
	except Exception as e:
		frappe.log_error(f"E-Wallet payment error: {str(e)[:100]}", "Midtrans Exception")
		return {
			"success": False,
			"error": ["Failed to create payment. Please try again."]
		}


def get_ewallet_display_name(ewallet_code):
	"""Get human-readable E-Wallet name from wallet code"""
	ewallet_names = {
		"gopay": "GoPay",
		"ovo": "OVO",
		"dana": "DANA",
		"shopeepay": "ShopeePay",
		"qris": "QRIS"
	}
	return ewallet_names.get(ewallet_code.lower(), ewallet_code.upper())


@frappe.whitelist()
def create_midtrans_bank_transfer(amount, currency="IDR", bank="bca", payment_method="bank_transfer"):
	"""Create bank transfer payment using Midtrans Core API"""
	team = get_current_team()
	
	if float(amount) < 1:
		return {
			"success": False,
			"error": "Minimum amount is 1.00"
		}
	
	try:
		# Get Midtrans configuration from Press Settings
		press_settings = frappe.get_single("Press Settings")
		is_sandbox = press_settings.midtrans_sandbox
		server_key = press_settings.get_password("midtrans_server_key")
		
		print(f"DEBUG:::: server_key {server_key}")

		if not server_key:
			return {
				"success": False,
				"error": "Midtrans server key not configured in Press Settings"
			}

		import requests
		import json
		from datetime import datetime, timedelta
		
		# Generate unique order ID (Midtrans requirements: max 50 chars, alphanumeric + dash/underscore only)
		doc_team = frappe.get_doc("Team", team)
		current_time = datetime.now()
		formatted_current_time = current_time.strftime("%d%m%Y%H%M%S")
		order_id = f"CREDITS-{doc_team.user}-{formatted_current_time}"

		# Prepare request data for Core API
		# Mandiri uses echannel payment type instead of bank_transfer
		if bank.lower() == 'mandiri':
			request_data = {
				"payment_type": "echannel",
				"transaction_details": {
					"order_id": order_id,
					"gross_amount": int(float(amount))
				},
				"echannel": {
					"bill_info1": order_id,  # Set bill_info1 with order_id
					"bill_info2": str(int(float(amount)))  # Set bill_info2 with amount
				}
			}
		else:
			# For other banks, use standard bank_transfer
			request_data = {
				"payment_type": "bank_transfer",
				"transaction_details": {
					"order_id": order_id,
					"gross_amount": int(float(amount))
				},
				"bank_transfer": {
					"bank": bank
				}
			}
		
		print(f"DEBUG:::: request_data: {json.dumps(request_data, indent=2)}")
		print(f"DEBUG:::: is_sandbox: {is_sandbox}")
		print(f"DEBUG:::: server_key length: {len(server_key) if server_key else 0}")
		
		# Prepare authorization header (Base64 encode server_key + ":")
		auth_string = f"{server_key}:"
		import base64
		auth_header = base64.b64encode(auth_string.encode()).decode()
		
		headers = {
			"Accept": "application/json",
			"Content-Type": "application/json",
			"Authorization": f"Basic {auth_header}"
		}
		
		# Use appropriate API URL based on sandbox/production mode
		base_url = "https://api.sandbox.midtrans.com/v2" if is_sandbox else "https://api.midtrans.com/v2"
		url = f"{base_url}/charge"
		
		response = requests.post(url, headers=headers, data=json.dumps(request_data))
		print(f"DEBUG:::response {response}")
		print(f"DEBUG::: {response.status_code}")
		print(f"DEBUG::: response {response.status_code == 200}")
		if response.status_code == 200:
			payment_data = response.json()
			
			print(f"DEBUG::::payment data {payment_data}")

			# Check if payment was created successfully using response status_code
			if payment_data.get("status_code") == "201":
				# Extract VA number based on bank and payment type
				va_number = None
				
				if bank.lower() == 'mandiri':
					# For Mandiri echannel, the VA number is in bill_key field
					va_number = payment_data.get('bill_key')
				else:
					# For other banks using bank_transfer, look in va_numbers array
					if 'va_numbers' in payment_data:
						for va in payment_data['va_numbers']:
							if va['bank'].lower() == bank.lower():
								va_number = va['va_number']
								break
				
				# Payment event will be created when webhook is received from Midtrans
				# Do not create payment event here to avoid duplicates
				
				print(f"DEBUG::::now should be return response")
				return {
					"success": True,
					"data": {
						"transaction_id": payment_data.get("transaction_id"),
						"order_id": order_id,
						"status": payment_data.get("transaction_status"),
						"amount": float(amount),
						"currency": currency,
						"bank": bank.upper(),  # Return bank name in uppercase for consistent display
						"bank_name": get_bank_display_name(bank),  # Human-readable bank name
						"va_number": va_number,
						"expiry_time": payment_data.get("expiry_time"),
						"payment_type": "bank_transfer"
					}
				}
			else:
				# Payment creation failed, return error from response
				error_messages = payment_data.get("error_messages", [])
				status_message = payment_data.get("status_message", "")
				
				if not error_messages and status_message:
					error_messages = [status_message]
				elif not error_messages:
					error_messages = [f"Payment creation failed with status {payment_data.get('status_code')}"]
				
				return {
					"success": False,
					"error": error_messages[0] if len(error_messages) == 1 else error_messages,
					"status_code": payment_data.get("status_code"),
					"raw_response": response.text[:500]
				}
		else:
			# Enhanced error handling
			error_data = {}
			try:
				error_data = response.json() if response.content else {}
			except:
				pass
				
			frappe.log_error(f"Bank transfer failed: {response.text[:100]}", "Midtrans Error")
			
			# Return more detailed error information
			error_messages = error_data.get("error_messages", [])
			status_message = error_data.get("status_message", "")
			
			if not error_messages and status_message:
				error_messages = [status_message]
			elif not error_messages:
				error_messages = [f"API request failed with status {response.status_code}"]
			
			return {
				"success": False,
				"error": error_messages[0] if len(error_messages) == 1 else error_messages,
				"status_code": response.status_code,
				"raw_response": response.text[:500]  # First 500 chars for debugging
			}
			
	except Exception as e:
		frappe.log_error(f"Bank transfer error: {str(e)[:100]}", "Midtrans Exception")
		return {
			"success": False,
			"error": ["Failed to create payment. Please try again."]
		}


@frappe.whitelist(allow_guest=True)
def verify_midtrans_ewallet_payment():
	"""Callback endpoint for E-Wallet payment verification"""
	try:
		# Get the JSON data from Midtrans callback
		import json
		callback_data = json.loads(frappe.request.data)
		
		transaction_id = callback_data.get('transaction_id')
		order_id = callback_data.get('order_id')
		transaction_status = callback_data.get('transaction_status')
		
		if transaction_status in ['settlement', 'capture']:
			# Payment successful - find and update the payment event
			payment_event = frappe.db.get_value(
				"Midtrans Payment Event", 
				{"midtrans_transaction_id": transaction_id}, 
				"name"
			)
			
			if payment_event:
				event_doc = frappe.get_doc("Midtrans Payment Event", payment_event)
				event_doc.transaction_status = transaction_status
				event_doc.midtrans_transaction_object = frappe.as_json(callback_data)
				event_doc.save(ignore_permissions=True)
				
				# Process the payment - add credits to team
				team = event_doc.team
				amount = callback_data.get('gross_amount', 0) / 100  # Convert from cents
				
				# Check if already processed
				if not frappe.db.exists("Balance Transaction", {"description": transaction_id}):
					team_doc = frappe.get_doc("Team", team)
					team_doc.allocate_credit_amount(
						amount=amount,
						source="Prepaid Credits",
						remark=transaction_id,
						type="Adjustment"
					)
		
		return {"status": "OK"}
		
	except Exception as e:
		frappe.log_error(f"E-Wallet callback error: {str(e)}", "Midtrans Callback")
		return {"status": "ERROR"}


@frappe.whitelist(allow_guest=True, methods=["GET"])
def download_qr_image():
	"""Proxy QR code image download to bypass CORS restrictions"""
	try:
		import requests
		from frappe.utils.response import build_response
		
		# Get QR URL from query parameters
		qr_url = frappe.form_dict.get('qr_url')
		if not qr_url:
			return {"error": "QR URL is required"}
		
		# Fetch the QR code image
		response = requests.get(qr_url, stream=True, timeout=10)
		response.raise_for_status()
		
		# Build file response
		frappe.local.response.filename = "qr-code.png"
		frappe.local.response.filecontent = response.content
		frappe.local.response.type = "download"
		
		# Set headers
		if not hasattr(frappe.local, 'response') or not frappe.local.response:
			frappe.local.response = frappe._dict()
			
		if not hasattr(frappe.local.response, 'headers'):
			frappe.local.response.headers = {}
			
		frappe.local.response.headers.update({
			'Content-Type': response.headers.get('Content-Type', 'image/png'),
			'Content-Disposition': 'attachment; filename="qr-code.png"',
			'Content-Length': str(len(response.content))
		})
		
	except requests.RequestException as e:
		frappe.log_error(f"QR download request failed: {str(e)}", "QR Download Error")
		return {"error": f"Failed to fetch QR code: {str(e)}"}
	except Exception as e:
		frappe.log_error(f"QR download failed: {str(e)}", "QR Download Error")
		return {"error": "Failed to download QR code image"}


@frappe.whitelist()
def check_midtrans_payment_status(transaction_id):
	"""Check payment status for a specific transaction"""
	try:
		# Get Midtrans configuration from Press Settings
		press_settings = frappe.get_single("Press Settings")
		is_sandbox = press_settings.midtrans_sandbox
		server_key = press_settings.midtrans_server_key
		
		if not server_key:
			return {
				"success": False,
				"error": "Midtrans server key not configured in Press Settings"
			}
		
		import requests
		
		# Prepare authorization header (Base64 encode server_key + ":")
		auth_string = f"{server_key}:"
		import base64
		auth_header = base64.b64encode(auth_string.encode()).decode()
		
		headers = {
			"Accept": "application/json",
			"Authorization": f"Basic {auth_header}"
		}
		
		# Use appropriate API URL based on sandbox/production mode
		base_url = "https://api.sandbox.midtrans.com/v2" if is_sandbox else "https://api.midtrans.com/v2"
		url = f"{base_url}/{transaction_id}/status"
		
		response = requests.get(url, headers=headers)
		
		if response.status_code == 200:
			payment_data = response.json()
			
			# Process settlement/capture status
			if payment_data.get("transaction_status") in ["settlement", "capture"]:
				# Payment completed - create balance transaction
				team = get_current_team()
				
				# Check if already processed
				if not frappe.db.exists("Balance Transaction", {"description": transaction_id}):
					amount = float(payment_data.get("gross_amount", 0))
					team.allocate_credit_amount(
						amount=amount,
						source="Prepaid Credits",
						remark=transaction_id,
						type="Adjustment"
					)
			
			return {
				"success": True,
				"status": payment_data.get("transaction_status"),
				"transaction_id": transaction_id,
				"payment_data": payment_data
			}
		else:
			return {
				"success": False,
				"error": "Failed to check payment status"
			}
			
	except Exception as e:
		frappe.log_error(f"Check status failed: {str(e)[:100]}", "Midtrans Error")
		return {
			"success": False,
			"error": "Failed to check payment status"
		}


@frappe.whitelist()
def upcoming_invoice():
	team = get_current_team(True)
	invoice = team.get_upcoming_invoice()

	if invoice:
		upcoming_invoice = invoice.as_dict()
		upcoming_invoice.formatted = make_formatted_doc(invoice, ["Currency"])
	else:
		upcoming_invoice = None

	return {
		"upcoming_invoice": upcoming_invoice,
		"available_credits": fmt_money(team.get_balance(), 2, team.currency),
	}


@frappe.whitelist()
def get_balance_credit():
	team = get_current_team(True)
	return team.get_balance()


@frappe.whitelist()
def past_invoices():
	return get_current_team(True).get_past_invoices()


@frappe.whitelist()
def invoices_and_payments():
	team = get_current_team(True)
	return team.get_past_invoices()


@frappe.whitelist()
def refresh_invoice_link(invoice):
	doc = frappe.get_doc("Invoice", invoice)
	return doc.refresh_stripe_payment_link()


@frappe.whitelist()
def balances():
	team = get_current_team()
	has_bought_credits = frappe.db.get_all(
		"Balance Transaction",
		filters={
			"source": ("in", ("Prepaid Credits", "Transferred Credits", "Free Credits")),
			"team": team,
			"docstatus": 1,
			"type": ("!=", "Partnership Fee"),
		},
		limit=1,
	)
	if not has_bought_credits:
		return []

	bt = frappe.qb.DocType("Balance Transaction")
	inv = frappe.qb.DocType("Invoice")
	query = (
		frappe.qb.from_(bt)
		.left_join(inv)
		.on(bt.invoice == inv.name)
		.select(
			bt.name,
			bt.creation,
			bt.amount,
			bt.currency,
			bt.source,
			bt.type,
			bt.ending_balance,
			bt.description,
			inv.period_start,
		)
		.where((bt.docstatus == 1) & (bt.team == team))
		.orderby(bt.creation, order=frappe.qb.desc)
	)

	data = query.run(as_dict=True)
	for d in data:
		d.formatted = dict(
			amount=fmt_money(d.amount, 2, d.currency),
			ending_balance=fmt_money(d.ending_balance, 2, d.currency),
		)

		if d.period_start:
			d.formatted["invoice_for"] = d.period_start.strftime("%B %Y")
	return data


def get_processed_balance_transactions(transactions: list[dict]):
	"""Cleans up transactions and adjusts ending balances accordingly"""

	cleaned_up_transations = get_cleaned_up_transactions(transactions)
	processed_balance_transactions = []
	for bt in reversed(cleaned_up_transations):
		if is_added_credits_bt(bt) and len(processed_balance_transactions) < 1:
			processed_balance_transactions.append(bt)
		elif is_added_credits_bt(bt):
			bt.ending_balance += processed_balance_transactions[
				-1
			].ending_balance  # Adjust the ending balance
			processed_balance_transactions.append(bt)
		elif bt.type == "Applied To Invoice":
			processed_balance_transactions.append(bt)

	return list(reversed(processed_balance_transactions))


def get_cleaned_up_transactions(transactions: list[dict]):
	"""Only picks Balance transactions that the users care about"""

	cleaned_up_transations = []
	for bt in transactions:
		if is_added_credits_bt(bt):
			cleaned_up_transations.append(bt)
			continue

		if bt.type == "Applied To Invoice" and not find(
			cleaned_up_transations, lambda x: x.invoice == bt.invoice
		):
			cleaned_up_transations.append(bt)
			continue
	return cleaned_up_transations


def is_added_credits_bt(bt):
	"""Returns `true` if credits were added and not some reverse transaction"""
	if not (
		bt.type == "Adjustment"
		and bt.source
		in (
			"Prepaid Credits",
			"Free Credits",
			"Transferred Credits",
		)  # Might need to re-think this
	):
		return False

	# Is not a reverse of a previous balance transaction
	bt.description = bt.description or ""
	return not bt.description.startswith("Reverse")


@frappe.whitelist()
def details():
	team = get_current_team(True)
	address = None
	if team.billing_address:
		address = frappe.get_doc("Address", team.billing_address)
		address_parts = [
			address.address_line1,
			address.city,
			address.state,
			address.country,
			address.pincode,
		]
		billing_address = ", ".join([d for d in address_parts if d])
	else:
		billing_address = ""

	return {
		"billing_name": team.billing_name,
		"billing_address": billing_address,
		"gstin": address.gstin if address else None,
	}


@frappe.whitelist()
def fetch_invoice_items(invoice):
	team = get_current_team()
	if frappe.db.get_value("Invoice", invoice, "team") != team:
		frappe.throw("Only team owners and members are permitted to download Invoice")

	return frappe.get_all(
		"Invoice Item",
		{"parent": invoice, "parenttype": "Invoice"},
		[
			"document_type",
			"document_name",
			"rate",
			"quantity",
			"amount",
			"plan",
			"description",
			"discount",
			"site",
		],
	)


@frappe.whitelist()
def get_customer_details(team):
	"""This method is called by frappe.io for creating Customer and Address"""
	team_doc = frappe.db.get_value("Team", team, "*")
	return {
		"team": team_doc,
		"address": frappe.get_doc("Address", team_doc.billing_address),
	}


@frappe.whitelist()
def create_payment_intent_for_micro_debit():
	team = get_current_team(True)
	stripe = get_stripe()

	micro_debit_charge_field = (
		"micro_debit_charge_usd" if team.currency == "USD" else "micro_debit_charge_inr"
	)
	amount = frappe.db.get_single_value("Press Settings", micro_debit_charge_field)

	intent = stripe.PaymentIntent.create(
		amount=int(amount * 100),
		currency=team.currency.lower(),
		customer=team.stripe_customer_id,
		description="Micro-Debit Card Test Charge",
		metadata={
			"payment_for": "micro_debit_test_charge",
		},
	)
	return {"client_secret": intent["client_secret"]}



@frappe.whitelist()
def create_payment_intent_for_partnership_fees():
	team = get_current_team(True)
	press_settings = frappe.get_cached_doc("Press Settings")
	metadata = {"payment_for": "partnership_fee"}
	fee_amount = press_settings.partnership_fee_usd

	if team.currency == "IDR":
		fee_amount = press_settings.partnership_fee_inr
		gst_amount = fee_amount * press_settings.gst_percentage
		fee_amount += gst_amount
		metadata.update({"gst": round(gst_amount, 2)})

	stripe = get_stripe()
	intent = stripe.PaymentIntent.create(
		amount=int(fee_amount * 100),
		currency=team.currency.lower(),
		customer=team.stripe_customer_id,
		description="Partnership Fee",
		metadata=metadata,
	)
	return {
		"client_secret": intent["client_secret"],
		"publishable_key": get_publishable_key(),
	}


@frappe.whitelist()
def create_payment_intent_for_buying_credits(amount):
	team = get_current_team(True)
	metadata = {"payment_for": "prepaid_credits"}
	total_unpaid = total_unpaid_amount()

	if amount < total_unpaid and not team.erpnext_partner:
		frappe.throw(f"Amount {amount} is less than the total unpaid amount {total_unpaid}.")

	if team.currency == "INR":
		gst_amount = amount * frappe.db.get_single_value("Press Settings", "gst_percentage")
		amount += gst_amount
		metadata.update({"gst": round(gst_amount, 2)})

	amount = round(amount, 2)
	stripe = get_stripe()
	intent = stripe.PaymentIntent.create(
		amount=int(amount * 100),
		currency=team.currency.lower(),
		customer=team.stripe_customer_id,
		description="Prepaid Credits",
		metadata=metadata,
	)
	return {
		"client_secret": intent["client_secret"],
		"publishable_key": get_publishable_key(),
	}


@frappe.whitelist()
def create_payment_intent_for_prepaid_app(amount, metadata):
	stripe = get_stripe()
	team = get_current_team(True)
	payment_method = frappe.get_value(
		"Stripe Payment Method", team.default_payment_method, "stripe_payment_method_id"
	)
	try:
		if not payment_method:
			intent = stripe.PaymentIntent.create(
				amount=amount * 100,
				currency=team.currency.lower(),
				customer=team.stripe_customer_id,
				description="Prepaid App Purchase",
				metadata=metadata,
			)
		else:
			intent = stripe.PaymentIntent.create(
				amount=amount * 100,
				currency=team.currency.lower(),
				customer=team.stripe_customer_id,
				description="Prepaid App Purchase",
				off_session=True,
				confirm=True,
				metadata=metadata,
				payment_method=payment_method,
				payment_method_options={"card": {"request_three_d_secure": "any"}},
			)

		return {
			"payment_method": payment_method,
			"client_secret": intent["client_secret"],
			"publishable_key": get_publishable_key(),
		}
	except stripe.error.CardError as e:
		err = e.error
		if err.code == "authentication_required":
			# Bring the customer back on-session to authenticate the purchase
			return {
				"error": "authentication_required",
				"payment_method": err.payment_method.id,
				"amount": amount,
				"card": err.payment_method.card,
				"publishable_key": get_publishable_key(),
				"client_secret": err.payment_intent.client_secret,
			}
		if err.code:
			# The card was declined for other reasons (e.g. insufficient funds)
			# Bring the customer back on-session to ask them for a new payment method
			return {
				"error": err.code,
				"payment_method": err.payment_method.id,
				"publishable_key": get_publishable_key(),
				"client_secret": err.payment_intent.client_secret,
			}


@frappe.whitelist()
def get_payment_methods():
	team = get_current_team()
	return frappe.get_doc("Team", team).get_payment_methods()


@frappe.whitelist()
def set_as_default(name):
	"""Set payment method as default based on gateway type"""
	team = get_current_team()
	default_gateway = frappe.db.get_single_value("Press Settings", "default_payment_gateway")
	
	if default_gateway == "Midtrans":
		payment_method = frappe.get_doc("Midtrans Payment Method", {"name": name, "team": team})
	else:
		payment_method = frappe.get_doc("Stripe Payment Method", {"name": name, "team": team})
	
	payment_method.set_default()


@frappe.whitelist()
def remove_payment_method(name):
	"""Remove payment method based on default payment gateway"""
	team = get_current_team()
	default_gateway = frappe.db.get_single_value("Press Settings", "default_payment_gateway")
	
	if default_gateway == "Midtrans":
		# Handle Midtrans payment method removal
		payment_method_count = frappe.db.count("Midtrans Payment Method", {"team": team})
		
		if has_unsettled_invoices(team) and payment_method_count == 1:
			return "Unpaid Invoices"
		
		payment_method = frappe.get_doc("Midtrans Payment Method", {"name": name, "team": team})
		payment_method.delete()
	else:
		# Handle Stripe payment method removal (default behavior)
		payment_method_count = frappe.db.count("Stripe Payment Method", {"team": team})
		
		if has_unsettled_invoices(team) and payment_method_count == 1:
			return "Unpaid Invoices"
		
		payment_method = frappe.get_doc("Stripe Payment Method", {"name": name, "team": team})
		payment_method.delete()
	
	return None


@frappe.whitelist()
def finalize_invoices():
	unsettled_invoices = frappe.get_all(
		"Invoice",
		{"team": get_current_team(), "status": ("in", ("Draft", "Unpaid"))},
		pluck="name",
	)

	for inv in unsettled_invoices:
		inv_doc = frappe.get_doc("Invoice", inv)
		inv_doc.finalize_invoice()


@frappe.whitelist()
def unpaid_invoices():
	team = get_current_team()
	return frappe.db.get_all(
		"Invoice",
		{
			"team": team,
			"status": ("in", ["Draft", "Unpaid", "Invoice Created"]),
			"type": "Subscription",
		},
		["name", "status", "period_end", "currency", "amount_due", "total"],
		order_by="creation asc",
	)


@frappe.whitelist()
def get_unpaid_invoices():
	team = get_current_team()
	unpaid_invoices = frappe.db.get_all(
		"Invoice",
		{
			"team": team,
			"status": "Unpaid",
			"type": "Subscription",
		},
		["name", "status", "period_end", "currency", "amount_due", "total", "stripe_invoice_url"],
		order_by="creation asc",
	)

	return unpaid_invoices  # noqa: RET504


@frappe.whitelist()
def change_payment_mode(mode):
	team = get_current_team(get_doc=True)

	team.payment_mode = mode
	if team.partner_email and mode == "Paid By Partner" and not team.billing_team:
		team.billing_team = frappe.db.get_value(
			"Team",
			{"enabled": 1, "erpnext_partner": 1, "partner_email": team.partner_email},
			"name",
		)
	if team.billing_team and mode != "Paid By Partner":
		team.billing_team = ""
	team.save()
	return


@frappe.whitelist()
def prepaid_credits_via_onboarding():
	"""When prepaid credits are bought, the balance is not immediately reflected.
	This method will check balance every second and then set payment_mode"""
	from time import sleep

	team = get_current_team(get_doc=True)

	seconds = 0
	# block until balance is updated
	while team.get_balance() == 0 or seconds > 20:
		seconds += 1
		sleep(1)
		frappe.db.rollback()

	team.payment_mode = "Prepaid Credits"
	team.save()


@frappe.whitelist()
def get_invoice_usage(invoice):
	team = get_current_team()
	# apply team filter for safety
	doc = frappe.get_doc("Invoice", {"name": invoice, "team": team})
	out = doc.as_dict()
	# a dict with formatted currency values for display
	out.formatted = make_formatted_doc(doc)
	out.invoice_pdf = doc.invoice_pdf or (doc.currency == "USD" and doc.get_pdf())
	return out


@frappe.whitelist()
def get_summary():
	team = get_current_team()
	invoices = frappe.get_all(
		"Invoice",
		filters={"team": team, "status": ("in", ["Paid", "Unpaid"])},
		fields=[
			"name",
			"status",
			"period_end",
			"payment_mode",
			"type",
			"currency",
			"amount_paid",
		],
		order_by="creation desc",
	)

	invoice_names = [x.name for x in invoices]
	grouped_invoice_items = get_grouped_invoice_items(invoice_names)

	for invoice in invoices:
		invoice.items = grouped_invoice_items.get(invoice.name, [])

	return invoices


def get_grouped_invoice_items(invoices: list[str]) -> dict:
	"""Takes a list of invoices (invoice names) and returns a dict of the form:
	{ "<invoice_name1>": [<invoice_items>], "<invoice_name2>": [<invoice_items>], }
	"""
	invoice_items = frappe.get_all(
		"Invoice Item",
		filters={"parent": ("in", invoices)},
		fields=[
			"amount",
			"document_name AS name",
			"document_type AS type",
			"parent",
			"quantity",
			"rate",
			"plan",
		],
	)

	grouped_items = groupby(invoice_items, key=lambda x: x["parent"])
	invoice_items_map = {}
	for invoice_name, items in grouped_items:
		invoice_items_map[invoice_name] = list(items)

	return invoice_items_map


@frappe.whitelist()
def after_card_add():
	clear_setup_intent()


@frappe.whitelist()
def setup_intent_success(setup_intent, address=None):
	setup_intent = frappe._dict(setup_intent)

	# refetching the setup intent to get mandate_id from stripe
	stripe = get_stripe()
	setup_intent = stripe.SetupIntent.retrieve(setup_intent.id)

	team = get_current_team(True)
	clear_setup_intent()
	mandate_reference = setup_intent.payment_method_options.card.mandate_options.reference
	payment_method = team.create_payment_method(
		setup_intent.payment_method,
		setup_intent.id,
		setup_intent.mandate,
		mandate_reference,
		set_default=True,
		verified_with_micro_charge=True,
	)
	if address:
		address = frappe._dict(address)
		team.update_billing_details(address)

	return {"payment_method_name": payment_method.name}


@frappe.whitelist()
def validate_gst(address, method=None):
	if isinstance(address, dict):
		address = frappe._dict(address)

	if address.country != "India":
		return

	if address.state not in states_with_tin:
		frappe.throw("Invalid State for India.")

	if not address.gstin:
		frappe.throw("GSTIN is required for Indian customers.")

	print(f"DEBUG:::address {address}")
	if address.gstin and address.gstin != "Not Applicable":
		if not GSTIN_FORMAT.match(address.gstin):
			frappe.throw("Invalid GSTIN. The input you've entered does not match the format of GSTIN.")

		tin_code = states_with_tin[address.state]
		if not address.gstin.startswith(tin_code):
			frappe.throw(f"GSTIN must start with {tin_code} for {address.state}.")

		validate_gstin_check_digit(address.gstin)


@frappe.whitelist()
def get_latest_unpaid_invoice():
	team = get_current_team()
	unpaid_invoices = frappe.get_all(
		"Invoice",
		{"team": team, "status": "Unpaid", "payment_attempt_count": (">", 0)},
		pluck="name",
		order_by="creation desc",
		limit=1,
	)

	if unpaid_invoices:
		unpaid_invoice = frappe.db.get_value(
			"Invoice",
			unpaid_invoices[0],
			["amount_due", "payment_mode", "amount_due", "currency"],
			as_dict=True,
		)
		if unpaid_invoice.payment_mode == "Prepaid Credits" and team_has_balance_for_invoice(unpaid_invoice):
			return None

		return unpaid_invoice
	return None


def team_has_balance_for_invoice(prepaid_mode_invoice):
	team = get_current_team(get_doc=True)
	return team.get_balance() >= prepaid_mode_invoice.amount_due


@frappe.whitelist()
def create_razorpay_order(amount, type=None):
	client = get_razorpay_client()
	team = get_current_team(get_doc=True)

	if team.currency == "INR":
		gst_amount = amount * frappe.db.get_single_value("Press Settings", "gst_percentage")
		amount += gst_amount

	amount = round(amount, 2)
	data = {
		"amount": int(amount * 100),
		"currency": team.currency,
		"notes": {
			"Description": "Order for Frappe Cloud Prepaid Credits",
			"Team (Frappe Cloud ID)": team.name,
			"gst": gst_amount if team.currency == "INR" else 0,
		},
	}
	if type and type == "Partnership Fee":
		data.get("notes").update({"Type": type})
	order = client.order.create(data=data)

	payment_record = frappe.get_doc(
		{"doctype": "Razorpay Payment Record", "order_id": order.get("id"), "team": team.name, "type": type}
	).insert(ignore_permissions=True)

	return {
		"order_id": order.get("id"),
		"key_id": client.auth[0],
		"payment_record": payment_record.name,
	}


@frappe.whitelist()
def handle_razorpay_payment_success(response):
	client = get_razorpay_client()
	client.utility.verify_payment_signature(response)

	payment_record = frappe.get_doc(
		"Razorpay Payment Record",
		{"order_id": response.get("razorpay_order_id")},
		for_update=True,
	)
	payment_record.update(
		{
			"payment_id": response.get("razorpay_payment_id"),
			"signature": response.get("razorpay_signature"),
			"status": "Captured",
		}
	)
	payment_record.save(ignore_permissions=True)


@frappe.whitelist()
def handle_razorpay_payment_failed(response):
	payment_record = frappe.get_doc(
		"Razorpay Payment Record",
		{"order_id": response["error"]["metadata"].get("order_id")},
		for_update=True,
	)

	payment_record.status = "Failed"
	payment_record.failure_reason = response["error"]["description"]
	payment_record.save(ignore_permissions=True)


@frappe.whitelist()
def total_unpaid_amount():
	team = get_current_team(get_doc=True)
	balance = team.get_balance()
	negative_balance = -1 * balance if balance < 0 else 0

	return (
		frappe.get_all(
			"Invoice",
			{"status": "Unpaid", "team": team.name, "type": "Subscription", "docstatus": ("!=", 2)},
			["sum(amount_due) as total"],
			pluck="total",
		)[0]
		or 0
	) + negative_balance


# Mpesa integrations, mpesa express
"""Send stk push to the user"""


def generate_stk_push(**kwargs):
	"""Generate stk push by making a API call to the stk push API."""
	args = frappe._dict(kwargs)
	partner_value = args.partner

	# Fetch the team document based on the extracted partner value
	partner = frappe.get_all("Team", filters={"user": partner_value, "erpnext_partner": 1}, pluck="name")
	if not partner:
		frappe.throw(_(f"Partner team {partner_value} not found"), title=_("Mpesa Express Error"))

	# Get Mpesa settings for the partner's team
	mpesa_setup = get_mpesa_setup_for_team(partner[0])
	try:
		callback_url = (
			get_request_site_address(True) + "/api/method/press.api.billing.verify_m_pesa_transaction"
		)
		env = "production" if not mpesa_setup.sandbox else "sandbox"
		# for sandbox, business shortcode is same as till number
		business_shortcode = (
			mpesa_setup.business_shortcode if env == "production" else mpesa_setup.till_number
		)
		connector = MpesaConnector(
			env=env,
			app_key=mpesa_setup.consumer_key,
			app_secret=mpesa_setup.get_password("consumer_secret"),
		)

		mobile_number = sanitize_mobile_number(args.sender)
		response = connector.stk_push(
			business_shortcode=business_shortcode,
			amount=args.amount_with_tax,
			passcode=mpesa_setup.get_password("pass_key"),
			callback_url=callback_url,
			reference_code=mpesa_setup.till_number,
			phone_number=mobile_number,
			description="Frappe Cloud Payment",
		)
		return response  # noqa: RET504

	except Exception:
		frappe.log_error("Mpesa Express Transaction Error")
		frappe.throw(
			_("Issue detected with Mpesa configuration, check the error logs for more details"),
			title=_("Mpesa Express Error"),
		)


@frappe.whitelist(allow_guest=True)
def verify_m_pesa_transaction(**kwargs):
	"""Verify the transaction result received via callback from STK."""
	transaction_response, request_id = parse_transaction_response(kwargs)
	status = handle_transaction_result(transaction_response, request_id)

	return {"status": status, "ResultDesc": transaction_response.get("ResultDesc")}


def parse_transaction_response(kwargs):
	"""Parse and validate the transaction response."""

	if "Body" not in kwargs or "stkCallback" not in kwargs["Body"]:
		frappe.log_error(title="Invalid transaction response format", message=kwargs)
		frappe.throw(_("Invalid transaction response format"))

	transaction_response = frappe._dict(kwargs["Body"]["stkCallback"])
	checkout_id = getattr(transaction_response, "CheckoutRequestID", "")
	if not isinstance(checkout_id, str):
		frappe.throw(_("Invalid Checkout Request ID"))

	return transaction_response, checkout_id


def handle_transaction_result(transaction_response, integration_request):
	"""Handle the logic based on ResultCode in the transaction response."""

	result_code = transaction_response.get("ResultCode")
	status = None

	if result_code == 0:
		try:
			status = "Completed"
			create_mpesa_request_log(
				transaction_response, "Host", "Mpesa Express", integration_request, None, status
			)

			create_mpesa_payment_record(transaction_response)
		except Exception as e:
			frappe.log_error(f"Mpesa: Transaction failed with error {e}")

	elif result_code == 1037:  # User unreachable (Phone off or timeout)
		status = "Failed"
		create_mpesa_request_log(
			transaction_response, "Host", "Mpesa Express", integration_request, None, status
		)
		frappe.log_error("Mpesa: User cannot be reached (Phone off or timeout)")

	elif result_code == 1032:  # User cancelled the request
		status = "Cancelled"
		create_mpesa_request_log(
			transaction_response, "Host", "Mpesa Express", integration_request, None, status
		)
		frappe.log_error("Mpesa: Request cancelled by user")

	else:  # Other failure codes
		status = "Failed"
		create_mpesa_request_log(
			transaction_response, "Host", "Mpesa Express", integration_request, None, status
		)
		frappe.log_error(f"Mpesa: Transaction failed with ResultCode {result_code}")
	return status


@frappe.whitelist()
def request_for_payment(**kwargs):
	"""request for payments"""
	team = get_current_team()

	kwargs.setdefault("team", team)
	args = frappe._dict(kwargs)
	update_tax_id_or_phone_no(team, args.tax_id, args.phone_number)

	amount = args.request_amount
	args.request_amount = frappe.utils.rounded(amount, 2)
	response = frappe._dict(generate_stk_push(**args))
	handle_api_mpesa_response("CheckoutRequestID", args, response)

	return response


def handle_api_mpesa_response(global_id, request_dict, response):
	"""Response received from API calls returns a global identifier for each transaction, this code is returned during the callback."""
	# check error response
	if response.requestId:
		req_name = response.requestId
		error = response
	else:
		# global checkout id used as request name
		req_name = getattr(response, global_id)
		error = None

	create_mpesa_request_log(request_dict, "Host", "Mpesa Express", req_name, error, output=response)

	if error:
		frappe.throw(_(response.errorMessage), title=_("Transaction Error"))


def create_mpesa_payment_record(transaction_response):
	"""Create a new entry in the Mpesa Payment Record for a successful transaction."""
	item_response = transaction_response.get("CallbackMetadata", {}).get("Item", [])
	mpesa_receipt_number = fetch_param_value(item_response, "MpesaReceiptNumber", "Name")
	transaction_time = fetch_param_value(item_response, "TransactionDate", "Name")
	phone_number = fetch_param_value(item_response, "PhoneNumber", "Name")
	transaction_id = transaction_response.get("CheckoutRequestID")
	amount = fetch_param_value(item_response, "Amount", "Name")
	merchant_request_id = transaction_response.get("MerchantRequestID")
	info = get_details_from_request_log(transaction_id)
	gateway_name = get_payment_gateway(info.partner)
	# Create a new entry in M-Pesa Payment Record
	data = {
		"transaction_id": transaction_id,
		"amount": amount,
		"team": frappe.get_value("Team", info.team, "user"),
		"tax_id": frappe.get_value("Team", info.team, "mpesa_tax_id"),
		"default_currency": "KES",
		"rate": info.requested_amount,
	}
	if frappe.db.exists("Mpesa Payment Record", {"transaction_id": transaction_id}):
		return
	mpesa_invoice, invoice_name = create_invoice_partner_site(data, gateway_name)
	try:
		payment_record = frappe.get_doc(
			{
				"doctype": "Mpesa Payment Record",
				"transaction_id": transaction_id,
				"transaction_time": parse_datetime(transaction_time),
				"transaction_type": "Mpesa Express",
				"team": info.team,
				"phone_number": str(phone_number),
				"amount": info.requested_amount,
				"grand_total": amount,
				"merchant_request_id": merchant_request_id,
				"payment_partner": info.partner,
				"amount_usd": info.amount_usd,
				"exchange_rate": info.exchange_rate,
				"local_invoice": mpesa_invoice,
				"mpesa_receipt_number": mpesa_receipt_number,
			}
		)
		payment_record.insert(ignore_permissions=True)
		payment_record.submit()
	except Exception:
		frappe.log_error("Failed to create Mpesa Payment Record")
		raise
	"""create payment partner transaction which will then create balance transaction"""
	create_payment_partner_transaction(
		info.team, info.partner, info.exchange_rate, info.amount_usd, info.requested_amount, gateway_name
	)
	mpesa_details = {
		"mpesa_receipt_number": mpesa_receipt_number,
		"mpesa_merchant_id": merchant_request_id,
		"mpesa_payment_record": payment_record.name,
		"mpesa_request_id": transaction_id,
		"mpesa_invoice": invoice_name,
	}
	create_balance_transaction_and_invoice(info.team, info.amount_usd, mpesa_details)

	frappe.msgprint(_("Mpesa Payment Record entry created successfully"))


def create_balance_transaction_and_invoice(team, amount, mpesa_details):
	try:
		balance_transaction = frappe.get_doc(
			doctype="Balance Transaction",
			team=team,
			source="Prepaid Credits",
			type="Adjustment",
			amount=amount,
			description=mpesa_details.get("mpesa_payment_record"),
			paid_via_local_pg=1,
		)
		balance_transaction.insert(ignore_permissions=True)
		balance_transaction.submit()

		invoice = frappe.get_doc(
			doctype="Invoice",
			team=team,
			type="Prepaid Credits",
			status="Paid",
			total=amount,
			amount_due=amount,
			amount_paid=amount,
			amount_due_with_tax=amount,
			due_date=frappe.utils.nowdate(),
			mpesa_merchant_id=mpesa_details.get("mpesa_merchant_id", ""),
			mpesa_receipt_number=mpesa_details.get("mpesa_receipt_number", ""),
			mpesa_request_id=mpesa_details.get("mpesa_request_id", ""),
			mpesa_payment_record=mpesa_details.get("mpesa_payment_record", ""),
			mpesa_invoice=mpesa_details.get("mpesa_invoice", ""),
		)
		invoice.append(
			"items",
			{
				"description": "Prepaid Credits",
				"document_type": "Balance Transaction",
				"document_name": balance_transaction.name,
				"quantity": 1,
				"rate": amount,
			},
		)
		invoice.insert(ignore_permissions=True)
		invoice.submit()

		_enqueue_finalize_unpaid_invoices_for_team(team)
	except Exception:
		frappe.log_error("Mpesa: Failed to create balance transaction and invoice")


def parse_datetime(date):
	from datetime import datetime

	return datetime.strptime(str(date), "%Y%m%d%H%M%S")


@frappe.whitelist()
def get_midtrans_invoice_pdf(invoice_name):
	"""Generate PDF for Midtrans invoice"""
	import os
	from frappe.utils.pdf import get_pdf
	
	# Get the invoice
	invoice = frappe.get_doc("Invoice", invoice_name)
	
	# Get team user if team exists
	team_user = None
	if invoice.team:
		team_user = frappe.db.get_value("Team", invoice.team, "user")
	
	# Get associated payment event
	payment_event = None
	if invoice.items:
		for item in invoice.items:
			if item.document_type == "Midtrans Payment Event":
				payment_event = frappe.get_doc("Midtrans Payment Event", item.document_name)
				break
	
	# Get template path
	template_path = os.path.join(
		frappe.get_app_path("press"),
		"press", "print_format", "midtrans_invoice", "midtrans_invoice.html"
	)
	
	# Read template
	with open(template_path, 'r') as f:
		template_content = f.read()
	
	# Render template with context
	from frappe.utils.jinja import get_jenv
	jenv = get_jenv()
	template = jenv.from_string(template_content)
	
	html_content = template.render(
		doc=invoice,
		team_user=team_user,
		payment_event=payment_event,
		frappe=frappe
	)
	
	# Generate PDF with minimal options
	pdf = get_pdf(html_content)
	
	# Return PDF response
	frappe.local.response.filename = f"midtrans_invoice_{invoice_name}.pdf"
	frappe.local.response.filecontent = pdf
	frappe.local.response.type = "download"
