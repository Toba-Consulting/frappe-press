# Copyright (c) 2025, Frappe and contributors
# For license information, please see license.txt
from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document

from press.utils import log_error
from press.utils.billing import verify_midtrans_notification


class InvalidMidtransWebhookEvent(Exception):
	http_status_code = 400


class MidtransWebhookLog(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		event_type: DF.Data | None
		invoice: DF.Link | None
		midtrans_payment_method: DF.Link | None
		order_id: DF.Data | None
		payload: DF.Code | None
		team: DF.Link | None
		transaction_id: DF.Data | None
		transaction_status: DF.Data | None
	# end: auto-generated types

	def validate(self):
		self.extract_webhook_data()

	def extract_webhook_data(self):
		"""Extract relevant data from webhook payload"""
		if not self.payload:
			return

		try:
			payload_data = frappe.parse_json(self.payload)
			
			self.transaction_id = payload_data.get("transaction_id")
			self.order_id = payload_data.get("order_id") 
			self.transaction_status = payload_data.get("transaction_status")
			self.event_type = payload_data.get("transaction_status", "notification")

			# Try to find associated invoice
			if self.order_id:
				invoice = frappe.db.get_value("Invoice", {"name": self.order_id})
				if invoice:
					self.invoice = invoice
					self.team = frappe.db.get_value("Invoice", invoice, "team")

		except Exception as e:
			frappe.log_error(f"Failed to extract webhook data: {str(e)}")

	def process_webhook(self):
		"""Process the webhook notification"""
		print(f"DEBUG:::its process webhook do")
		try:
			from press.press.doctype.midtrans_payment_event.midtrans_payment_event import create_payment_event_from_webhook
			
			if not self.payload:
				print("DEBUG:::No payload found in webhook log")
				return

			payload_data = frappe.parse_json(self.payload)
			print(f"DEBUG:::payload_data {payload_data}")
			print(f"DEBUG:::Processing webhook for transaction_status: {payload_data.get('transaction_status')}")
			
			# Create payment event
			create_payment_event_from_webhook(payload_data)
			
			frappe.db.commit()
			print("DEBUG:::Webhook processing completed successfully")
			
		except Exception as e:
			print(f"DEBUG:::Error in process_webhook: {str(e)}")
			print(f"DEBUG:::Error traceback: {frappe.get_traceback()}")
			log_error("Midtrans Webhook Processing Error", webhook_log=self.name, error=str(e))
			raise


@frappe.whitelist(allow_guest=True)
def midtrans_webhook_handler():
	"""Handle incoming Midtrans webhook notifications"""
	try:
		# Get the payload from request
		data = frappe.request.get_json()
		print(f"DEBUG::::data webhook handlre {data}")
		signature_key = frappe.request.headers.get("X-Midtrans-Signature")
		
		if not data:
			frappe.throw(_("Invalid webhook payload"))

		# Verify signature if provided
		if signature_key:
			if not verify_midtrans_notification(data, signature_key):
				raise InvalidMidtransWebhookEvent("Invalid webhook signature")
		else:
			print("DEBUG:::No signature key provided, skipping signature verification")

		print(f"DEBUG:::signature key {signature_key}")
		print(f"DEBUG:::transaction_status {data.get('transaction_status')}")
		print(f"DEBUG:::order_id {data.get('order_id')}")
		print(f"DEBUG:::status_code {data.get('status_code')}")
		print(f"DEBUG:::gross_amount {data.get('gross_amount')}")
		
		# Create webhook log with unique name combining payment status and transaction_id
		transaction_id = data.get('transaction_id', frappe.generate_hash(length=8))
		payment_status = data.get('transaction_status', 'unknown')
		
		# Map settlement to settle for consistent naming
		if payment_status == 'settlement':
			payment_status = 'settle'
		
		webhook_log_name = f"midtrans-{payment_status}-{transaction_id}"
		
		webhook_log = frappe.get_doc({
			"doctype": "Midtrans Webhook Log",
			"name": webhook_log_name,
			"payload": frappe.as_json(data)
		})

		print(f"DEBUG::::webhook_log {webhook_log}")

		webhook_log.insert(ignore_permissions=True)
		print(f"DEBUG::::webhook_log insert success {webhook_log}")
		# Process the webhook
		webhook_log.process_webhook()
		
		return {"status": "success"}

	except InvalidMidtransWebhookEvent as e:
		frappe.respond_as_web_page(
			_("Invalid Webhook"),
			_("The webhook signature could not be verified."),
			http_status_code=400,
		)
		return

	except Exception as e:
		log_error("Midtrans Webhook Handler Error", error=str(e))
		frappe.respond_as_web_page(
			_("Webhook Error"),
			_("There was an error processing the webhook."),
			http_status_code=500,
		)
		return