# Copyright (c) 2024, Frappe Technologies and contributors
# License: MIT. See LICENSE

from frappe.model.document import Document


class ContactCategory(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		link_to_user: DF.Link | None
		name1: DF.Data
	# end: auto-generated types

	pass 