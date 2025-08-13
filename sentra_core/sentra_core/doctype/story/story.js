frappe.ui.form.on('Story', {
	refresh(frm) {
		frm.disable_save();
		['itineraries','facts','evidence'].forEach((table)=>{
			const grid = frm.fields_dict && frm.fields_dict[table] && frm.fields_dict[table].grid;
			if (grid) {
				grid.cannot_add_rows = true;
				grid.cannot_delete_rows = true;
				grid.refresh();
			}
		});
	}
});

