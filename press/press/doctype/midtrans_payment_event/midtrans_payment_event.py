# Copyright (c) 2025, Frappe and contributors
# For license information, please see license.txt
from __future__ import annotations

import frappe
from frappe.model.document import Document


class MidtransPaymentEvent(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		event_type: DF.Literal["Transaction", "Capture", "Settle", "Cancel", "Deny", "Expire"]
		invoice: DF.Link | None
		midtrans_order_id: DF.Data | None
		midtrans_transaction_id: DF.Data | None
		midtrans_transaction_object: DF.Code | None
		payment_status: DF.Literal["", "Paid", "Unpaid", "Pending"]
		payment_type: DF.Data | None
		team: DF.Link | None
		transaction_status: DF.Literal["", "capture", "settle", "pending", "deny", "cancel", "expire", "failure"]
	# end: auto-generated types

	def validate(self):
		self.map_transaction_status_to_payment_status()

	def map_transaction_status_to_payment_status(self):
		"""Map Midtrans transaction status to our payment status"""
		status_mapping = {
			"capture": "Paid",
			"settle": "Paid",
			"pending": "Pending",
			"deny": "Unpaid",
			"cancel": "Unpaid",
			"expire": "Unpaid",
			"failure": "Unpaid"
		}
		
		if self.transaction_status in status_mapping:
			self.payment_status = status_mapping[self.transaction_status]

	def after_insert(self):
		"""Process payment event after insertion"""
		if self.payment_status == "Paid" and self.invoice:
			self.mark_invoice_as_paid()

	def mark_invoice_as_paid(self):
		"""Mark the associated invoice as paid"""
		if not self.invoice:
			return
			
		try:
			invoice = frappe.get_doc("Invoice", self.invoice)
			if invoice.status != "Paid":
				invoice.status = "Paid"
				invoice.save(ignore_permissions=True)
				frappe.db.commit()
		except Exception as e:
			frappe.log_error(f"Failed to mark invoice {self.invoice} as paid: {str(e)}")


@frappe.whitelist()
def create_payment_event_from_webhook(notification_data):
	"""Create a payment event from Midtrans webhook notification"""
	try:
		event = frappe.get_doc({
			"doctype": "Midtrans Payment Event",
			"midtrans_transaction_id": notification_data.get("transaction_id"),
			"midtrans_order_id": notification_data.get("order_id"),
			"transaction_status": notification_data.get("transaction_status"),
			"payment_type": notification_data.get("payment_type"),
			"event_type": "Transaction",  # Default event type
			"midtrans_transaction_object": frappe.as_json(notification_data)
		})
		
		# Try to find associated invoice by order_id
		if notification_data.get("order_id"):
			invoice = frappe.db.get_value("Invoice", {"name": notification_data.get("order_id")})
			if invoice:
				event.invoice = invoice
				event.team = frappe.db.get_value("Invoice", invoice, "team")
		
		event.insert(ignore_permissions=True)
		return event.name
		
	except Exception as e:
		frappe.log_error(f"Failed to create Midtrans payment event: {str(e)}")
		raise