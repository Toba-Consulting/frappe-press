# Copyright (c) 2025, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe.tests.utils import FrappeTestCase


class TestMidtransPaymentEvent(FrappeTestCase):
	def test_transaction_status_mapping(self):
		event = frappe.get_doc({
			"doctype": "Midtrans Payment Event",
			"transaction_status": "capture",
			"event_type": "Transaction"
		})
		event.validate()
		
		self.assertEqual(event.payment_status, "Paid")

	def test_pending_status_mapping(self):
		event = frappe.get_doc({
			"doctype": "Midtrans Payment Event",
			"transaction_status": "pending",
			"event_type": "Transaction"
		})
		event.validate()
		
		self.assertEqual(event.payment_status, "Pending")

	def test_failed_status_mapping(self):
		event = frappe.get_doc({
			"doctype": "Midtrans Payment Event",
			"transaction_status": "deny",
			"event_type": "Transaction"
		})
		event.validate()
		
		self.assertEqual(event.payment_status, "Unpaid")