# Copyright (c) 2024, arun and contributors
# For license information, please see license.txt

import frappe


def execute():
    """Reduce gender options to just Male and Female"""
    # Get all genders except Male and Female
    genders_to_remove = frappe.get_all(
        "Gender",
        filters={"name": ["not in", ["Male", "Female"]]},
        pluck="name"
    )
    
    if genders_to_remove:
        # Update any contacts using these genders to blank
        for gender in genders_to_remove:
            frappe.db.sql("""
                UPDATE `tabContact` 
                SET gender = NULL 
                WHERE gender = %s
            """, gender)
            
            # Delete the gender option
            frappe.delete_doc("Gender", gender, force=True)
        
        frappe.db.commit()