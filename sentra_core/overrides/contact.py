# import frappe
from frappe import _
import frappe
from frappe.contacts.doctype.contact.contact import Contact


# Hook functions for doc_events
def validate(doc, method):
	"""Hook function called during validation"""
	# The CustomContact class already handles validation
	pass


def on_update(doc, method):
	"""Hook function called after update"""
	# Add any post-update logic here if needed
	pass


def before_delete(doc, method):
	"""Hook function called before deletion"""
	validate_delete_permissions(doc)


def validate_delete_permissions(doc):
	"""Validate if contact can be deleted"""
	# Check if contact is linked to other documents
	linked_docs = []
	
	try:
		# Check Dynamic Links
		dynamic_links = frappe.get_all("Dynamic Link", 
			filters={
				"link_doctype": "Contact",
				"link_name": doc.name
			},
			fields=["parent", "parenttype"]
		)
		
		for link in dynamic_links:
			linked_docs.append(f"{link.parenttype}: {link.parent}")
	
	except Exception as e:
		frappe.log_error(f"Error checking dynamic links: {str(e)}")
	
	try:
		# Check if this contact is someone's manager
		managed_contacts = frappe.get_all("Contact",
			filters={"manager": doc.name, "name": ["!=", doc.name]},
			fields=["name", "full_name"]
		)
		
		for managed in managed_contacts:
			linked_docs.append(f"Manager of: {managed.full_name} ({managed.name})")
	
	except Exception as e:
		frappe.log_error(f"Error checking manager references: {str(e)}")
	
	try:
		# Check communications (but don't block deletion for these)
		communications = frappe.get_all("Communication",
			filters={"reference_doctype": "Contact", "reference_name": doc.name},
			limit=1
		)
		
		if communications:
			# Just log but don't prevent deletion
			frappe.msgprint(
				_("Contact has communication history which will be preserved."),
				indicator="orange"
			)
	
	except Exception as e:
		frappe.log_error(f"Error checking communications: {str(e)}")
	
	# Only prevent deletion for critical links
	critical_links = [link for link in linked_docs if not link.startswith("Communication:")]
	
	if critical_links:
		if len(critical_links) > 10:
			linked_summary = critical_links[:10] + [f"... and {len(critical_links) - 10} more"]
		else:
			linked_summary = critical_links
			
		frappe.throw(
			_("Cannot delete Contact {0}. It is linked to:\n{1}\n\nPlease remove these references first.").format(
				doc.full_name or doc.name,
				"\n".join(linked_summary)
			)
		)


class CustomContact(Contact):
	def get_formatted_data(self):
		"""Return formatted contact data for API responses"""
		data = self.as_dict()
		
		# Add computed fields
		data['age'] = self.calculate_age() if self.dob else None
		data['years_of_service'] = self.calculate_years_of_service() if self.date_of_joining else None
		data['primary_contact_methods'] = self.get_primary_contact_methods()
		data['linked_entities'] = self.get_linked_entities()
		
		return data
	
	def calculate_age(self):
		"""Calculate age from date of birth"""
		if not self.dob:
			return None
		
		from datetime import datetime
		try:
			dob_date = datetime.strptime(str(self.dob), '%Y-%m-%d')
			today = datetime.now()
			age = today.year - dob_date.year
			if today.month < dob_date.month or (today.month == dob_date.month and today.day < dob_date.day):
				age -= 1
			return age
		except:
			return None
	
	def calculate_years_of_service(self):
		"""Calculate years of service for employees"""
		if not self.date_of_joining or self.contact_type != "Employee":
			return None
		
		from datetime import datetime
		try:
			doj_date = datetime.strptime(str(self.date_of_joining), '%Y-%m-%d')
			today = datetime.now()
			years = today.year - doj_date.year
			if today.month < doj_date.month or (today.month == doj_date.month and today.day < doj_date.day):
				years -= 1
			return max(0, years)
		except:
			return None
	
	def get_primary_contact_methods(self):
		"""Get primary contact methods in a structured format"""
		methods = {}
		
		if self.email_id:
			methods['email'] = self.email_id
		if self.mobile_no:
			methods['mobile'] = self.mobile_no
		if self.phone:
			methods['phone'] = self.phone
		if hasattr(self, 'instagram') and self.instagram:
			methods['instagram'] = self.instagram
		
		return methods
	
	def get_linked_entities(self):
		"""Get entities linked to this contact"""
		linked = []
		
		# Get Dynamic Links
		dynamic_links = frappe.get_all("Dynamic Link", 
			filters={
				"link_doctype": "Contact",
				"link_name": self.name
			},
			fields=["parent", "parenttype"]
		)
		
		for link in dynamic_links:
			linked.append({
				"doctype": link.parenttype,
				"name": link.parent
			})
		
		return linked

	def validate(self):
		# Handle child table primary fields first
		self.sync_primary_email_and_phone()
		
		# First, run the original validation from the parent class
		super().validate()

		# Custom validations
		self.validate_mandatory_contact_info()
		self.validate_contact_type()
		self.validate_gstin()
		self.validate_phone_numbers()
		self.validate_email()
		self.validate_employee_fields()
		self.validate_vendor_fields()
		self.validate_contact_type_change()
		self.set_full_name()

	def validate_contact_type_change(self):
		"""Validate contact type changes on update"""
		if self.get_doc_before_save():
			old_doc = self.get_doc_before_save()
			
			# Check if contact_type is being changed
			if old_doc.contact_type != self.contact_type:
				# Validate type change scenarios
				if old_doc.contact_type == "Employee" and self.contact_type != "Employee":
					# Check if employee has any dependencies
					if self.employee_code:
						frappe.msgprint(
							_("Contact type changed from Employee. Consider clearing employee-specific fields."),
							indicator="orange"
						)
				
				# If changing TO Employee, ensure required fields
				if old_doc.contact_type != "Employee" and self.contact_type == "Employee":
					if not self.employee_code:
						frappe.throw(_("Employee Code is required when changing contact type to Employee"))
				
				# If changing TO Vendor, ensure required fields
				if old_doc.contact_type != "Vendor" and self.contact_type == "Vendor":
					if not self.vendor_type:
						frappe.throw(_("Vendor Type is required when changing contact type to Vendor"))

	def sync_primary_email_and_phone(self):
		"""Sync primary email and phone from child tables to main fields"""
		# Handle email_ids child table
		if self.email_ids:
			# Ensure only one primary email
			primary_count = sum(1 for email in self.email_ids if email.is_primary)
			
			if primary_count > 1:
				# Too many primaries, keep only the first one
				found_first = False
				for email in self.email_ids:
					if email.is_primary and not found_first:
						found_first = True
					elif email.is_primary and found_first:
						email.is_primary = 0
			elif primary_count == 0 and len(self.email_ids) > 0:
				# No primary set, make the first one primary
				self.email_ids[0].is_primary = 1
			
			# Sync primary email to main field
			for email in self.email_ids:
				if email.is_primary:
					self.email_id = email.email_id
					break
			else:
				# No primary found, clear main field
				if self.email_ids:  # If there are emails but no primary
					self.email_id = ""
		
		# Handle phone_nos child table
		if self.phone_nos:
			# Ensure only one primary phone and one primary mobile
			primary_phone_count = sum(1 for phone in self.phone_nos if phone.is_primary_phone)
			primary_mobile_count = sum(1 for phone in self.phone_nos if phone.is_primary_mobile_no)
			
			# Fix multiple primaries
			if primary_phone_count > 1:
				found_first = False
				for phone in self.phone_nos:
					if phone.is_primary_phone and not found_first:
						found_first = True
					elif phone.is_primary_phone and found_first:
						phone.is_primary_phone = 0
			
			if primary_mobile_count > 1:
				found_first = False
				for phone in self.phone_nos:
					if phone.is_primary_mobile_no and not found_first:
						found_first = True
					elif phone.is_primary_mobile_no and found_first:
						phone.is_primary_mobile_no = 0
			
			# If no primary is set, make the first one primary based on type
			if primary_phone_count == 0 and primary_mobile_count == 0 and len(self.phone_nos) > 0:
				import re
				phone_num = self.phone_nos[0].phone
				mobile_pattern = r'^(\+91[-.\s]?)?[6-9]\d{9}$'
				clean_phone = re.sub(r'[-.\s]', '', phone_num)
				
				if re.match(mobile_pattern, clean_phone):
					self.phone_nos[0].is_primary_mobile_no = 1
				else:
					self.phone_nos[0].is_primary_phone = 1
			
			# Sync primary phone/mobile to main fields
			self.phone = ""
			self.mobile_no = ""
			for phone in self.phone_nos:
				if phone.is_primary_phone:
					self.phone = phone.phone
				if phone.is_primary_mobile_no:
					self.mobile_no = phone.phone

	def validate_mandatory_contact_info(self):
		"""Validate that at least one contact method is provided"""
		# Check if at least one of these is provided:
		# 1. email_id (or email_ids child table)
		# 2. mobile_no (or phone_nos child table)
		# 3. instagram
		
		has_email = bool(self.email_id) or bool(self.email_ids)
		has_phone = bool(self.mobile_no) or bool(self.phone) or bool(self.phone_nos)
		has_instagram = bool(getattr(self, 'instagram', None))
		
		if not (has_email or has_phone or has_instagram):
			frappe.throw(
				_("At least one contact method is required: Email, Mobile Number, or Instagram ID")
			)

	def validate_contact_type(self):
		"""Validate contact type and category relationship"""
		if self.contact_type and self.contact_category:
			# Define valid categories for each contact type
			valid_categories = {
				"Customer": ["Individual", "Organization"],
				"Vendor": ["Individual", "Organization"],
				"Employee": ["User", "Non-User"]
			}
			
			if self.contact_type in valid_categories:
				valid_cats = valid_categories.get(self.contact_type, [])
				if self.contact_category not in valid_cats:
					# Show warning for invalid category combinations
					frappe.msgprint(
						_("Contact Category '{0}' is not typical for Contact Type '{1}'. Expected categories are: {2}").format(
							self.contact_category, self.contact_type, ", ".join(valid_cats)
						),
						indicator="orange"
					)

	def validate_gstin(self):
		"""Validate GSTIN format if provided"""
		if self.gstin:
			import re
			# GSTIN format: 2 digits (state code) + 10 chars (PAN) + 1 digit + 1 default 'Z' + 1 check digit
			gstin_pattern = r'^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$'
			
			if not re.match(gstin_pattern, self.gstin.upper()):
				frappe.throw(_("Invalid GSTIN format. GSTIN should be 15 characters with proper format."))
			
			self.gstin = self.gstin.upper()

	def validate_phone_numbers(self):
		"""Validate phone number formats"""
		import re
		
		# Indian phone number pattern (with or without +91)
		phone_pattern = r'^(\+91[-.\s]?)?[6-9]\d{9}$'
		
		if self.mobile_no:
			# Remove spaces and special characters for validation
			clean_mobile = re.sub(r'[-.\s]', '', self.mobile_no)
			if not re.match(phone_pattern, clean_mobile):
				frappe.throw(_("Invalid mobile number format. Please enter a valid 10-digit Indian mobile number."))
		
		if self.phone:
			# Allow landline numbers with STD code
			landline_pattern = r'^(\+91[-.\s]?)?[0-9]{2,4}[-.\s]?[0-9]{6,8}$'
			clean_phone = re.sub(r'[-.\s]', '', self.phone)
			if not re.match(phone_pattern, clean_phone) and not re.match(landline_pattern, clean_phone):
				frappe.throw(_("Invalid phone number format."))

	def validate_email(self):
		"""Validate email and check for duplicates"""
		if self.email_id:
			# Frappe already validates email format
			# Check for duplicates
			existing = frappe.db.get_value("Contact", 
				{"email_id": self.email_id, "name": ["!=", self.name]}, 
				"name"
			)
			
			if existing:
				frappe.msgprint(
					_("Another contact ({0}) already exists with email {1}").format(existing, self.email_id),
					indicator="orange"
				)

	def validate_employee_fields(self):
		"""Validate employee-specific fields"""
		if self.contact_type == "Employee":
			# Employee code is mandatory for employees
			if not self.employee_code:
				frappe.throw(_("Employee Code is mandatory for Employee contacts"))
			
			# Check employee code uniqueness
			existing = frappe.db.get_value("Contact",
				{"employee_code": self.employee_code, "name": ["!=", self.name]},
				"name"
			)
			if existing:
				frappe.throw(_("Employee Code {0} already exists for contact {1}").format(
					self.employee_code, existing
				))
			
			# Validate manager hierarchy - also check circular references
			if self.manager and self.manager == self.name:
				frappe.throw(_("Employee cannot be their own manager"))
			
			# Check for circular manager hierarchy (A -> B -> A)
			if self.manager:
				self.check_circular_manager_hierarchy(self.manager, [self.name])
			
			# Validate date of joining
			if self.date_of_joining and self.dob:
				from datetime import datetime
				try:
					dob_date = datetime.strptime(str(self.dob), '%Y-%m-%d')
					doj_date = datetime.strptime(str(self.date_of_joining), '%Y-%m-%d')
					
					# Employee should be at least 18 years old when joining
					age_at_joining = (doj_date - dob_date).days / 365.25
					if age_at_joining < 18:
						frappe.throw(_("Employee must be at least 18 years old at the time of joining"))
				except ValueError:
					frappe.throw(_("Invalid date format for Date of Birth or Date of Joining"))
			
			# Validate employee status changes
			if self.get_doc_before_save():
				old_doc = self.get_doc_before_save()
				if old_doc.employee_status == "Active" and self.employee_status == "Inactive":
					frappe.msgprint(
						_("Employee status changed to Inactive. This may affect system access."),
						indicator="orange"
					)

	def check_circular_manager_hierarchy(self, manager_id, hierarchy_chain):
		"""Check for circular references in manager hierarchy"""
		if manager_id in hierarchy_chain:
			frappe.throw(_("Circular manager hierarchy detected: {0}").format(" -> ".join(hierarchy_chain + [manager_id])))
		
		# Get the manager's manager
		manager_of_manager = frappe.db.get_value("Contact", manager_id, "manager")
		if manager_of_manager:
			self.check_circular_manager_hierarchy(manager_of_manager, hierarchy_chain + [manager_id])

	def validate_vendor_fields(self):
		"""Validate vendor-specific fields"""
		if self.contact_type == "Vendor":
			if not self.vendor_type:
				frappe.throw(_("Vendor Type is mandatory for Vendor contacts"))
			
			# If vendor type is GST registered, GSTIN is mandatory
			if self.vendor_type in ["Airline", "Hotel", "Transport"] and not self.gstin:
				frappe.msgprint(
					_("GSTIN is recommended for {0} vendors").format(self.vendor_type),
					indicator="orange"
				)

	def set_full_name(self):
		"""Set full name from first, middle, and last names"""
		if self.contact_category == "Organization":
			# For organizations, full name is the first name (organization name)
			self.full_name = self.first_name or ""
		else:
			# For individuals, combine names
			name_parts = []
			if self.salutation:
				name_parts.append(self.salutation)
			if self.first_name:
				name_parts.append(self.first_name)
			if self.middle_name:
				name_parts.append(self.middle_name)
			if self.last_name:
				name_parts.append(self.last_name)
			
			self.full_name = " ".join(name_parts)
		
		# If still no full name, use email or mobile
		if not self.full_name:
			self.full_name = self.email_id or self.mobile_no or "Unnamed Contact"
