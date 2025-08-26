// Copyright (c) 2025, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on("Midtrans Payment Method", {
	refresh: function(frm) {
		// Add custom buttons or functionality here
		if (!frm.is_new()) {
			frm.add_custom_button("Delete Payment Method", function() {
				frappe.confirm(
					"Are you sure you want to delete this payment method?",
					function() {
						frm.call("delete").then(() => {
							frappe.set_route("List", "Midtrans Payment Method");
						});
					}
				);
			});
		}
	}
});