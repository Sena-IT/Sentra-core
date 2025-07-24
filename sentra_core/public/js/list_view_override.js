// Copyright (c) 2024, arun and contributors
// For license information, please see license.txt

// Override list view settings functionality
frappe.provide("frappe.views");

// Store original functions
const original_get_list_settings = frappe.views.get_list_settings;
const original_set_list_settings = frappe.views.set_list_settings;

// Override get_list_settings
if (frappe.views.get_list_settings) {
    frappe.views.get_list_settings = function(doctype, settings_name) {
        if (!settings_name) {
            settings_name = "default";
        }
        return frappe.call({
            method: "sentra_core.overrides.listview.get_list_settings",
            args: {
                doctype: doctype,
                settings_name: settings_name
            }
        });
    };
}

// Override set_list_settings
if (frappe.views.set_list_settings) {
    frappe.views.set_list_settings = function(doctype, settings_name, values) {
        if (!settings_name) {
            settings_name = "default";
        }
        return frappe.call({
            method: "sentra_core.overrides.listview.set_list_settings",
            args: {
                doctype: doctype,
                settings_name: settings_name,
                values: values
            }
        });
    };
}

// Add get_all_list_settings function
frappe.views.get_all_list_settings = function(doctype) {
    return frappe.call({
        method: "sentra_core.overrides.listview.get_all_list_settings",
        args: {
            doctype: doctype
        }
    });
};