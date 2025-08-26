# Copyright (c) 2025, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe.tests.utils import FrappeTestCase


class TestMidtransWebhookLog(FrappeTestCase):
	def test_webhook_data_extraction(self):
		payload = {
			"transaction_id": "test-txn-123",
			"order_id": "test-order-456", 
			"transaction_status": "capture",
			"gross_amount": "100000"
		}
		
		webhook_log = frappe.get_doc({
			"doctype": "Midtrans Webhook Log",
			"name": "test-webhook-log",
			"payload": frappe.as_json(payload)
		})
		
		webhook_log.validate()
		
		self.assertEqual(webhook_log.transaction_id, "test-txn-123")
		self.assertEqual(webhook_log.order_id, "test-order-456")
		self.assertEqual(webhook_log.transaction_status, "capture")
		self.assertEqual(webhook_log.event_type, "capture")

	def test_invalid_payload_handling(self):
		webhook_log = frappe.get_doc({
			"doctype": "Midtrans Webhook Log",
			"name": "test-invalid-webhook",
			"payload": "invalid-json"
		})
		
		# Should not raise exception, just log error
		webhook_log.validate()
		
		# Fields should remain empty
		self.assertIsNone(webhook_log.transaction_id)
		self.assertIsNone(webhook_log.order_id)