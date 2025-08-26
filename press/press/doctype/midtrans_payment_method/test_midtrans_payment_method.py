# Copyright (c) 2025, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe.tests.utils import FrappeTestCase


class TestMidtransPaymentMethod(FrappeTestCase):
	def setUp(self):
		self.team = frappe.get_doc({
			"doctype": "Team",
			"name": "test-team",
			"title": "Test Team"
		})
		if not frappe.db.exists("Team", "test-team"):
			self.team.insert()

	def test_payment_method_creation(self):
		payment_method = frappe.get_doc({
			"doctype": "Midtrans Payment Method",
			"team": "test-team",
			"name_on_card": "Test User",
			"last_4": "1234",
			"brand": "visa",
			"card_type": "credit"
		})
		payment_method.insert()
		
		self.assertTrue(frappe.db.exists("Midtrans Payment Method", payment_method.name))
		
		# Clean up
		payment_method.delete()

	def test_default_payment_method(self):
		# Create two payment methods
		pm1 = frappe.get_doc({
			"doctype": "Midtrans Payment Method",
			"team": "test-team",
			"name_on_card": "Test User 1",
			"last_4": "1234",
			"is_default": 1
		})
		pm1.insert()
		
		pm2 = frappe.get_doc({
			"doctype": "Midtrans Payment Method", 
			"team": "test-team",
			"name_on_card": "Test User 2",
			"last_4": "5678",
			"is_default": 1
		})
		pm2.insert()
		
		# First one should no longer be default
		pm1.reload()
		self.assertEqual(pm1.is_default, 0)
		self.assertEqual(pm2.is_default, 1)
		
		# Clean up
		pm1.delete()
		pm2.delete()

	def tearDown(self):
		# Clean up any remaining test data
		frappe.db.rollback()