app_name = "sentra_core"
app_title = "Sentra Core"
app_publisher = "arun"
app_description = "Core customizations for Sentra Platform"
app_email = "it@sena.services"
app_license = "unlicense"

# Apps
# ------------------

required_apps = ["frappe"]

# Each item in the list will be shown as an app in the apps page
# add_to_apps_screen = [
# 	{
# 		"name": "sentra_core",
# 		"logo": "/assets/sentra_core/logo.png",
# 		"title": "Sentra Core",
# 		"route": "/sentra_core",
# 		"has_permission": "sentra_core.api.permission.has_app_permission"
# 	}
# ]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/sentra_core/css/sentra_core.css"
app_include_js = [
    "/assets/sentra_core/js/contact_override.js",
    "/assets/sentra_core/js/communication_override.js",
    "/assets/sentra_core/js/list_view_override.js"
]

# include js, css files in header of web template
# web_include_css = "/assets/sentra_core/css/sentra_core.css"
# web_include_js = "/assets/sentra_core/js/sentra_core.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "sentra_core/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
doctype_js = {
    "Contact" : "public/js/contact.js",
    "Communication": "public/js/communication.js"
}
doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "sentra_core/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# automatically load and sync documents of this doctype from downstream apps
# importable_doctypes = [doctype_1]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "sentra_core.utils.jinja_methods",
# 	"filters": "sentra_core.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "sentra_core.install.before_install"
after_install = "sentra_core.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "sentra_core.uninstall.before_uninstall"
# after_uninstall = "sentra_core.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

before_app_install = "sentra_core.overrides.override_email_functions"
# after_app_install = "sentra_core.utils.after_app_install"

# Boot session overrides
boot_session = "sentra_core.overrides.override_email_functions"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "sentra_core.utils.before_app_uninstall"
# after_app_uninstall = "sentra_core.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "sentra_core.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# DocType Class
# ---------------
# Override standard doctype classes

override_doctype_class = {
	"Contact": "sentra_core.overrides.contact.CustomContact",
}

# Document Events
# ---------------
# Hook on document methods and events

doc_events = {
    "User": {
        "after_insert": "sentra_core.overrides.user.after_insert"
    },
    "Contact": {
        "validate": "sentra_core.overrides.contact.validate",
        "on_update": "sentra_core.overrides.contact.on_update",
        "before_delete": "sentra_core.overrides.contact.before_delete"
    },
    "Communication": {
        "validate": "sentra_core.overrides.communication.validate",
        "after_insert": "sentra_core.story.engine.update_from_comm",
    },
    "Trip": {
        "after_insert": "sentra_core.story.engine.update_from_business",
        "on_update": "sentra_core.story.engine.update_from_business",
    },
    "Itinerary": {
        "after_insert": "sentra_core.story.engine.update_from_business",
        "on_update": "sentra_core.story.engine.update_from_business",
    },
}

# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"sentra_core.tasks.all"
# 	],
# 	"daily": [
# 		"sentra_core.tasks.daily"
# 	],
# 	"hourly": [
# 		"sentra_core.tasks.hourly"
# 	],
# 	"weekly": [
# 		"sentra_core.tasks.weekly"
# 	],
# 	"monthly": [
# 		"sentra_core.tasks.monthly"
# 	],
# }

# Testing
# -------

# before_tests = "sentra_core.install.before_tests"

# Overriding Methods
# ------------------------------
#
override_whitelisted_methods = {
    "frappe.desk.listview.get_list_settings": "sentra_core.overrides.listview.get_list_settings",
    "frappe.desk.listview.set_list_settings": "sentra_core.overrides.listview.set_list_settings",
    "frappe.desk.listview.get_all_list_settings": "sentra_core.overrides.listview.get_all_list_settings"
}
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "sentra_core.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["sentra_core.utils.before_request"]
# after_request = ["sentra_core.utils.after_request"]

# Job Events
# ----------
# before_job = ["sentra_core.utils.before_job"]
# after_job = ["sentra_core.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"sentra_core.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# Fixtures
# --------
fixtures = [
    {
        "dt": "Custom Field",
        "filters": [
            ["dt", "in", ["Contact", "Communication", "User"]]
        ]
    },
    {
        "dt": "Property Setter",
        "filters": [
            ["doc_type", "in", ["Contact", "Communication", "List View Settings"]]
        ]
    }
]

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

