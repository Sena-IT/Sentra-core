# Copyright (c) 2024, arun and contributors
# For license information, please see license.txt

from frappe import _

def get_data():
    return [
        {
            "module_name": "Sentra Core",
            "category": "Modules",
            "label": _("Sentra Core"),
            "color": "#00bcd4",
            "icon": "octicon octicon-package",
            "type": "module",
            "description": "Sentra Travel Services Core Customizations"
        }
    ]