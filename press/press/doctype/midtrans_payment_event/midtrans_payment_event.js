// Copyright (c) 2025, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on("Midtrans Payment Event", {
	refresh: function(frm) {
		// Add custom buttons or functionality here
		if (frm.doc.midtrans_transaction_object) {
			frm.add_custom_button("View Transaction Details", function() {
				let transaction_data = JSON.parse(frm.doc.midtrans_transaction_object);
				let dialog = new frappe.ui.Dialog({
					title: "Midtrans Transaction Details",
					fields: [
						{
							fieldtype: "HTML",
							options: `<pre>${JSON.stringify(transaction_data, null, 2)}</pre>`
						}
					]
				});
				dialog.show();
			});
		}
	}
});