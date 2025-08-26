// Copyright (c) 2025, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on("Midtrans Webhook Log", {
	refresh: function(frm) {
		if (!frm.is_new()) {
			frm.add_custom_button("Process Webhook", function() {
				frm.call("process_webhook").then(() => {
					frappe.msgprint("Webhook processed successfully");
					frm.reload_doc();
				});
			});

			if (frm.doc.payload) {
				frm.add_custom_button("View Payload", function() {
					let payload_data = JSON.parse(frm.doc.payload);
					let dialog = new frappe.ui.Dialog({
						title: "Webhook Payload",
						fields: [
							{
								fieldtype: "HTML",
								options: `<pre>${JSON.stringify(payload_data, null, 2)}</pre>`
							}
						]
					});
					dialog.show();
				});
			}
		}
	}
});