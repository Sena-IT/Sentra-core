"""
AI Assistant API endpoints
Handles AI chat messages and notifications
"""

import frappe
from frappe import _

@frappe.whitelist()
def get_unread_message_count():
    """
    Get the count of unread AI assistant messages for the current user
    
    Returns:
        dict: Contains unread_count and optionally latest messages
    """
    try:
        # For now, check CRM Notifications that are AI-related
        # You can customize this based on your actual message storage
        filters = {
            "to_user": frappe.session.user,
            "read": False
        }
        
        # Count unread notifications
        # You may want to filter by type if you have AI-specific message types
        unread_count = frappe.db.count("CRM Notification", filters=filters)
        
        # Optionally get the latest few unread messages
        latest_messages = frappe.db.get_list(
            "CRM Notification",
            filters=filters,
            fields=["name", "notification_text", "creation", "from_user"],
            order_by="creation desc",
            limit=5
        )
        
        return {
            "success": True,
            "unread_count": unread_count,
            "latest_messages": latest_messages,
            "timestamp": frappe.utils.now()
        }
        
    except Exception as e:
        frappe.log_error(f"Error getting unread message count: {str(e)}", "AI Assistant API")
        return {
            "success": False,
            "unread_count": 0,
            "error": str(e)
        }

@frappe.whitelist()
def mark_messages_as_read(message_ids=None):
    """
    Mark AI assistant messages as read
    
    Args:
        message_ids: List of message IDs to mark as read, or None for all
    
    Returns:
        dict: Success status and number of messages marked
    """
    try:
        filters = {
            "to_user": frappe.session.user,
            "read": False
        }
        
        if message_ids:
            filters["name"] = ["in", message_ids]
        
        # Get all matching notifications
        notifications = frappe.get_all("CRM Notification", filters=filters)
        
        marked_count = 0
        for notification in notifications:
            doc = frappe.get_doc("CRM Notification", notification.name)
            doc.read = True
            doc.save(ignore_permissions=True)
            marked_count += 1
        
        frappe.db.commit()
        
        return {
            "success": True,
            "marked_count": marked_count
        }
        
    except Exception as e:
        frappe.log_error(f"Error marking messages as read: {str(e)}", "AI Assistant API")
        return {
            "success": False,
            "marked_count": 0,
            "error": str(e)
        }

@frappe.whitelist()
def get_ai_chat_history(limit=50):
    """
    Get AI chat history for the current user
    
    Args:
        limit: Maximum number of messages to retrieve
    
    Returns:
        dict: Chat history and metadata
    """
    try:
        # This would fetch from your actual AI chat storage
        # For now, using CRM Notifications as example
        messages = frappe.db.get_list(
            "CRM Notification",
            filters={"to_user": frappe.session.user},
            fields=["*"],
            order_by="creation desc",
            limit=limit
        )
        
        return {
            "success": True,
            "messages": messages,
            "total_count": len(messages)
        }
        
    except Exception as e:
        frappe.log_error(f"Error getting AI chat history: {str(e)}", "AI Assistant API")
        return {
            "success": False,
            "messages": [],
            "error": str(e)
        }