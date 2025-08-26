# Copyright (c) 2025, Frappe and contributors
# For license information, please see license.txt
from __future__ import annotations

import frappe
from frappe.contacts.address_and_contact import load_address_and_contact
from frappe.model.document import Document

from press.api.client import dashboard_whitelist
from press.overrides import get_permission_query_conditions_for_doctype
from press.utils import log_error
from press.utils.billing import get_midtrans
from press.utils.telemetry import capture


class MidtransPaymentMethod(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		brand: DF.Data | None
		card_type: DF.Literal["", "credit", "debit"]
		expiry_month: DF.Data | None
		expiry_year: DF.Data | None
		is_default: DF.Check
		is_verified_with_micro_charge: DF.Check
		last_4: DF.Data | None
		midtrans_customer_id: DF.Data | None
		midtrans_payment_method_id: DF.Data | None
		midtrans_token: DF.Data | None
		midtrans_transaction_id: DF.Data | None
		name_on_card: DF.Data | None
		team: DF.Link
	# end: auto-generated types

	dashboard_fields = [
		"name",
		"team",
		"brand",
		"last_4",
		"expiry_month", 
		"expiry_year",
		"is_default",
	]

	def after_insert(self):
		capture("added_card", "fc_signup")

	def on_update(self):
		if self.is_default:
			# Set all other payment methods for this team to non-default
			frappe.db.sql(
				"""
				UPDATE `tabMidtrans Payment Method` 
				SET is_default = 0 
				WHERE team = %s AND name != %s
			""",
				[self.team, self.name],
			)

	def on_trash(self):
		capture("removed_card", "fc_signup")

	@dashboard_whitelist()
	def delete(self):
		try:
			midtrans = get_midtrans()
			# Midtrans doesn't have a direct delete payment method API
			# The token/card data is managed through their system
			# Just remove from our local database
			
			frappe.delete_doc(self.doctype, self.name, ignore_permissions=True)
			return "Payment method deleted successfully"
		except Exception as e:
			log_error("Midtrans Payment Method Deletion Error", payment_method=self.name, error=str(e))
			frappe.throw(f"Failed to delete payment method: {str(e)}")

	def get_address_display(self):
		return load_address_and_contact(self.doctype, self.name).get("address_text", "")

	def validate(self):
		self.validate_team()

	def validate_team(self):
		if not frappe.db.exists("Team", self.team):
			frappe.throw("Invalid team specified")

	@staticmethod
	def get_permission_query_conditions(user):
		return get_permission_query_conditions_for_doctype("Midtrans Payment Method")

	def get_doc(self, doc):
		doc.update({"address_display": self.get_address_display()})
		return doc


def get_permission_query_conditions(user):
	return MidtransPaymentMethod.get_permission_query_conditions(user)


@frappe.whitelist()
@dashboard_whitelist()
def get_payment_methods():
	"""Get all payment methods for current team"""
	from press.utils import get_current_team
	
	team = get_current_team()
	return frappe.get_all(
		"Midtrans Payment Method",
		filters={"team": team},
		fields=MidtransPaymentMethod.dashboard_fields,
		order_by="is_default desc, creation desc"
	)