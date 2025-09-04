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
			"settlement": "Paid",
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
		print(f"DEBUG:::this is invoice!!!!")
		if self.payment_status == "Paid":
			if self.invoice:
				self.mark_invoice_as_paid()
			else:
				# Handle prepaid credits - create balance transaction and invoice
				self.create_credit_balance_transaction()
			# Cancel other pending transactions for the same team
			self.cancel_other_pending_transactions()
		elif self.payment_status == "Pending" and not self.invoice:
			# Create pending invoice for credit purchases
			print(f"DEBUG:::this is invoice!!!!")
			self.create_pending_credit_invoice()

	def mark_invoice_as_paid(self):
		"""Mark the associated invoice as paid"""
		if not self.invoice:
			return
			
		try:
			invoice = frappe.get_doc("Invoice", self.invoice)
			if invoice.status != "Paid":
				invoice.status = "Paid"
				invoice.save(ignore_permissions=True)
				invoice.submit()
				frappe.db.commit()
		except Exception as e:
			frappe.log_error(f"Failed to mark invoice {self.invoice} as paid: {str(e)}")

	def create_pending_credit_invoice(self):
		"""Create pending invoice for credit purchases"""
		if not self.team:
			frappe.log_error(f"No team found for payment event {self.name}")
			return
			
		try:
			# Cancel any existing pending invoices for the same team before creating new one
			self.cancel_existing_pending_invoices()
			# Parse transaction data to get amount
			transaction_data = frappe.parse_json(self.midtrans_transaction_object) if self.midtrans_transaction_object else {}
			gross_amount = transaction_data.get("gross_amount", 0)
			
			if not gross_amount:
				frappe.log_error(f"No amount found in payment event {self.name}")
				return
			
			# Create pending invoice for the prepaid credits
			invoice = frappe.get_doc({
				"doctype": "Invoice",
				"team": self.team,
				"type": "Prepaid Credits",
				"status": "Unpaid",
				"total": float(gross_amount),
				"amount_due": float(gross_amount),
				"amount_paid": 0,
				"due_date": frappe.utils.nowdate(),
				"currency": "IDR"  # Default currency for Midtrans
			})
			
			# Add invoice item
			invoice.append("items", {
				"description": "Prepaid Credits (Pending Payment)",
				"document_type": "Midtrans Payment Event",
				"document_name": self.name,
				"quantity": 1,
				"rate": float(gross_amount),
				"amount": float(gross_amount)
			})

			invoice.insert(ignore_permissions=True)
			print(f"DEBUG:::this is invoice!!!!")
			# Link the invoice to the payment event
			self.db_set("invoice", invoice.name)
			self.save(ignore_permissions=True)
			
			frappe.db.commit()
			
		except Exception as e:
			frappe.log_error(f"Failed to create pending credit invoice for {self.name}: {str(e)}")

	def create_credit_balance_transaction(self):
		"""Create balance transaction and update invoice to paid for prepaid credits"""
		if not self.team:
			frappe.log_error(f"No team found for payment event {self.name}")
			return
			
		try:
			# Parse transaction data to get amount
			transaction_data = frappe.parse_json(self.midtrans_transaction_object) if self.midtrans_transaction_object else {}
			gross_amount = transaction_data.get("gross_amount", 0)
			
			if not gross_amount:
				frappe.log_error(f"No amount found in payment event {self.name}")
				return
			
			# Check if already processed to avoid duplicate transactions
			existing_transaction = frappe.db.exists("Balance Transaction", {
				"description": self.midtrans_transaction_id,
				"team": self.team
			})
			
			if existing_transaction:
				frappe.log_error(f"Balance transaction already exists for {self.midtrans_transaction_id}")
				return
			
			# Create balance transaction
			balance_transaction = frappe.get_doc({
				"doctype": "Balance Transaction",
				"team": self.team,
				"source": "Prepaid Credits",
				"type": "Adjustment",
				"amount": float(gross_amount),
				"description": self.midtrans_transaction_id
			})
			balance_transaction.insert(ignore_permissions=True)
			balance_transaction.submit()
			
			# Update existing invoice to paid status
			if self.invoice:
				invoice = frappe.get_doc("Invoice", self.invoice)
				invoice.status = "Paid"
				invoice.amount_paid = float(gross_amount)
				# Update invoice item to reference balance transaction
				if invoice.items:
					invoice.items[0].document_type = "Balance Transaction"
					invoice.items[0].document_name = balance_transaction.name
					invoice.items[0].description = "Prepaid Credits"
				invoice.save(ignore_permissions=True)
				invoice.submit()
				frappe.db.commit()
			else:
				frappe.log_error(f"No invoice found for payment event {self.name} - invoice should have been created in pending state")
			
			frappe.db.commit()
			
		except Exception as e:
			frappe.log_error(f"Failed to create credit balance transaction for {self.name}: {str(e)}")

	def cancel_existing_pending_invoices(self):
		"""Cancel existing pending Prepaid Credits invoices and payment events for the same team when creating a new one"""
		if not self.team:
			return
			
		try:
			# Find existing pending Prepaid Credits invoices for the same team
			pending_invoices = frappe.get_all("Invoice", 
				filters={
					"team": self.team,
					"type": "Prepaid Credits",
					"status": "Unpaid"
				},
				fields=["name"]
			)
			
			# Set each pending invoice to Empty
			for invoice_data in pending_invoices:
				try:
					invoice = frappe.get_doc("Invoice", invoice_data.name)
					invoice.status = "Empty"
					invoice.save(ignore_permissions=True)
					frappe.db.commit()
					print(f"DEBUG:::Set pending invoice {invoice_data.name} to Empty")
					
				except Exception as e:
					frappe.log_error(f"Failed to set invoice {invoice_data.name} to Empty: {str(e)}")
			
			# Find and cancel existing pending payment events for the same team (excluding current one)
			pending_payment_events = frappe.get_all("Midtrans Payment Event",
				filters={
					"team": self.team,
					"payment_status": "Pending",
					"name": ["!=", self.name]
				},
				fields=["name"]
			)
			
			# Cancel each pending payment event
			for event_data in pending_payment_events:
				try:
					payment_event = frappe.get_doc("Midtrans Payment Event", event_data.name)
					payment_event.payment_status = "Unpaid"
					payment_event.transaction_status = "cancel"
					payment_event.save(ignore_permissions=True)
					frappe.db.commit()
					print(f"DEBUG:::Cancelled pending payment event {event_data.name}")
					
				except Exception as e:
					frappe.log_error(f"Failed to cancel payment event {event_data.name}: {str(e)}")
					
		except Exception as e:
			frappe.log_error(f"Failed to cancel existing pending invoices and payment events for team {self.team}: {str(e)}")

	def cancel_other_pending_transactions(self):
		"""Cancel other pending Midtrans payment events for the same team when one gets paid"""
		if not self.team:
			return
			
		try:
			# Find all other pending payment events for the same team (excluding current one)
			pending_events = frappe.get_all("Midtrans Payment Event", 
				filters={
					"team": self.team,
					"payment_status": "Pending",
					"name": ["!=", self.name]
				},
				fields=["name"]
			)
			
			# Cancel each pending event
			for event in pending_events:
				try:
					payment_event = frappe.get_doc("Midtrans Payment Event", event.name)
					payment_event.payment_status = "Unpaid"
					payment_event.transaction_status = "cancel"
					payment_event.save(ignore_permissions=True)
					
					# If there's an associated pending invoice, cancel it too
					if payment_event.invoice:
						invoice = frappe.get_doc("Invoice", payment_event.invoice)
						if invoice.status in ["Draft", "Unpaid"]:
							invoice.status = "Empty"
							invoice.save(ignore_permissions=True)
							
					frappe.db.commit()
					print(f"DEBUG:::Cancelled pending payment event {event.name}")
					
				except Exception as e:
					frappe.log_error(f"Failed to cancel pending payment event {event.name}: {str(e)}")
					
		except Exception as e:
			frappe.log_error(f"Failed to cancel other pending transactions for team {self.team}: {str(e)}")


@frappe.whitelist()
def create_payment_event_from_webhook(notification_data):
	"""Create a payment event from Midtrans webhook notification"""
	try:
		transaction_id = notification_data.get("transaction_id")
		order_id = notification_data.get("order_id")
		
		# Check if payment event already exists (to handle duplicate webhooks)
		existing_event = None
		if transaction_id:
			existing_event = frappe.db.get_value("Midtrans Payment Event", 
				{"midtrans_transaction_id": transaction_id}, "name")
		
		if existing_event:
			# Update existing event with latest webhook data
			event = frappe.get_doc("Midtrans Payment Event", existing_event)
			old_status = event.transaction_status
			old_payment_status = event.payment_status
			
			# Update with new data
			transaction_status = notification_data.get("transaction_status")
			# Map settlement to settle for consistent naming
			if transaction_status == 'settlement':
				transaction_status = 'settle'
			
			event.transaction_status = transaction_status
			event.payment_type = notification_data.get("payment_type")
			event.midtrans_transaction_object = frappe.as_json(notification_data)
			
			# Trigger mapping to update payment_status based on new transaction_status
			event.map_transaction_status_to_payment_status()
			event.save(ignore_permissions=True)
			
			# Process payment if status changed from non-paid to paid
			if old_payment_status != "Paid" and event.payment_status == "Paid":
				if event.invoice:
					# For invoices (both existing invoices and pending credit invoices)
					if event.team and not frappe.db.exists("Balance Transaction", 
						{"description": event.midtrans_transaction_id, "team": event.team}):
						# This is a credit purchase - create balance transaction
						event.create_credit_balance_transaction()
					else:
						# Regular invoice payment
						event.mark_invoice_as_paid()
				elif event.team:
					# No invoice but has team - direct credit purchase
					event.create_credit_balance_transaction()
				
				# Cancel other pending transactions for the same team
				event.cancel_other_pending_transactions()
			
			return event.name
		else:
			# Create new payment event
			transaction_status = notification_data.get("transaction_status")
			# Map settlement to settle for consistent naming
			if transaction_status == 'settlement':
				transaction_status = 'settle'
			
			event = frappe.get_doc({
				"doctype": "Midtrans Payment Event",
				"midtrans_transaction_id": transaction_id,
				"midtrans_order_id": order_id,
				"transaction_status": transaction_status,
				"payment_type": notification_data.get("payment_type"),
				"event_type": "Transaction",
				"midtrans_transaction_object": frappe.as_json(notification_data)
			})
			
			# Try to find associated invoice by order_id
			if order_id:
				invoice = frappe.db.get_value("Invoice", {"name": order_id})
				if invoice:
					event.invoice = invoice
					event.team = frappe.db.get_value("Invoice", invoice, "team")
			
			# If no invoice found, try to extract team from order_id for credit purchases
			if not event.team and order_id:
				if order_id.startswith("CREDITS-"):
					# Extract team from CREDITS-{team}-{timestamp} format
					team_part = order_id.replace("CREDITS-", "").split("-")[0]
					if frappe.db.exists("Team", {"user": team_part}):
						event.team = frappe.db.get_value("Team", {"user": team_part}, "name")
				elif "-" in order_id:
					# Extract team from {team}-{hash} format
					team_part = order_id.split("-")[0]
					if frappe.db.exists("Team", team_part):
						event.team = team_part
			
			event.insert(ignore_permissions=True)
			return event.name
		
	except Exception as e:
		frappe.log_error(f"Failed to create Midtrans payment event: {str(e)}")
		raise