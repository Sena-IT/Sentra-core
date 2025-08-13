from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

import json

import frappe
from frappe.utils import now_datetime

from sentra_core.story import rules, normalize
from sentra_core.story.comm_extract import extract_itinerary_ref_from_comm


def ensure_story(contact_name: str):
    story_name = frappe.db.get_value("Story", {"contact": contact_name})
    if story_name:
        return frappe.get_doc("Story", story_name)

    story = frappe.get_doc({
        "doctype": "Story",
        "contact": contact_name,
        "stage": "Inquiry",
        "story_version": 1,
        "last_built_at": now_datetime(),
        "last_touch_from": "system",
        "last_touch_reason": "ensure_story",
    })
    story.insert(ignore_permissions=True)
    return story


def _serialize_value(value: Any) -> str:
    if isinstance(value, (dict, list)):
        return json.dumps(value, default=str)
    return str(value) if value is not None else ""


def upsert_fact(
    story,
    key: str,
    value: Any,
    *,
    source_doctype: Optional[str] = None,
    source_name: Optional[str] = None,
    precedence: str = "business_object",
) -> None:
    existing = None
    for row in story.get("facts") or []:
        if row.key == key:
            existing = row
            break

    if existing:
        existing.value = _serialize_value(value)
        existing.precedence = precedence
        if source_doctype and source_name:
            existing.source_doc_type = source_doctype
            existing.source_doc = source_name
        existing.last_seen_at = now_datetime()
    else:
        story.append(
            "facts",
            {
                "key": key,
                "value": _serialize_value(value),
                "precedence": precedence,
                "source_doc_type": source_doctype,
                "source_doc": source_name,
                "last_seen_at": now_datetime(),
            },
        )
    story.save(ignore_permissions=True)


def append_event(
    story,
    event_type: str,
    *,
    source_doctype: Optional[str] = None,
    source_name: Optional[str] = None,
    diff: Optional[Dict[str, Any]] = None,
    actor: str = "system",
) -> None:
    event = frappe.get_doc(
        {
            "doctype": "Story Event",
            "contact": story.contact,
            "event_type": event_type,
            "source_doctype": source_doctype,
            "source_ref": source_name,
            "diff": json.dumps(diff or {}),
            "actor": actor,
            "created_at": now_datetime(),
        }
    )
    event.insert(ignore_permissions=True)


def choose_and_update_stage(
    story,
    *,
    has_contact: bool,
    has_itinerary: bool,
    itinerary_statuses: List[str],
    trip_ready: bool,
    proposal_sent_flag: bool,
    mutation_reason: str,
    source_doctype: Optional[str] = None,
    source_name: Optional[str] = None,
    event_type: str = "business_object_updated",
) -> None:
    old_stage = story.stage or "Inquiry"
    new_stage = rules.choose_stage(
        old_stage, has_contact, has_itinerary, itinerary_statuses, trip_ready, proposal_sent_flag
    )
    if new_stage != old_stage:
        story.stage = new_stage
        story.story_version = (story.story_version or 0) + 1
        story.last_built_at = now_datetime()
        story.last_touch_from = "system"
        story.last_touch_reason = mutation_reason
        story.save(ignore_permissions=True)
        append_event(
            story,
            event_type,
            source_doctype=source_doctype,
            source_name=source_name,
            diff={"stage": {"from": old_stage, "to": new_stage}},
            actor="system",
        )


def _itineraries_for_trip(trip_name: str) -> List[Dict[str, Any]]:
    return frappe.get_all(
        "Itinerary",
        filters={"trip": trip_name},
        fields=["name", "status", "valid_from", "valid_to"],
        order_by="creation asc",
    )


def mark_proposal_sent(contact: str, itinerary: str, comm_name: str, sent_at) -> None:
    story = ensure_story(contact)
    upsert_fact(
        story,
        "proposal.itinerary",
        itinerary,
        source_doctype="Communication",
        source_name=comm_name,
    )
    upsert_fact(
        story,
        "proposal.sent_at",
        str(sent_at),
        source_doctype="Communication",
        source_name=comm_name,
    )

    # compute current metrics
    has_itinerary = bool(story.get("itineraries"))
    itinerary_statuses = [row.status for row in (story.get("itineraries") or []) if getattr(row, "status", None)]
    trip_ready = False
    if story.primary_trip:
        trip = frappe.get_doc("Trip", story.primary_trip)
        intent = normalize.intent_from_trip(trip)
        trip_ready = rules.trip_ready_for_proposal(intent)

    choose_and_update_stage(
        story,
        has_contact=True,
        has_itinerary=has_itinerary,
        itinerary_statuses=itinerary_statuses,
        trip_ready=trip_ready,
        proposal_sent_flag=True,
        mutation_reason="first_itinerary_sent",
        source_doctype="Communication",
        source_name=comm_name,
    )


def _choose_primary_trip_for_contact(contact: str) -> Optional[str]:
    from frappe.utils import getdate, nowdate

    trips = frappe.get_all(
        "Trip",
        filters={"customer": contact},
        fields=["name", "start_date", "creation"],
        order_by="creation desc",
    )
    if not trips:
        return None
    today = getdate(nowdate())
    future = [t for t in trips if t.get("start_date") and getdate(t["start_date"]) >= today]
    if future:
        # nearest future start_date
        future.sort(key=lambda t: getdate(t["start_date"]))
        return future[0]["name"]
    # else most recently created
    return trips[0]["name"]


def update_from_business(doc, method: Optional[str] = None) -> None:
    if doc.doctype.lower() == "trip":
        trip = doc
        contact = trip.customer
        if not contact:
            return
        story = ensure_story(contact)

        # maintain primary_trip heuristic
        new_primary = _choose_primary_trip_for_contact(contact)
        if new_primary and story.primary_trip != new_primary:
            story.primary_trip = new_primary
            story.save(ignore_permissions=True)

        intent = normalize.intent_from_trip(trip)
        trip_ready = rules.trip_ready_for_proposal(intent)

        itins = _itineraries_for_trip(trip.name)
        has_itinerary = bool(itins)
        itinerary_statuses = [i["status"] for i in itins]

        facts_dict = normalize.story_facts_to_dict(story)
        proposal_sent_flag = rules.proposal_sent(facts_dict)

        choose_and_update_stage(
            story,
            has_contact=True,
            has_itinerary=has_itinerary,
            itinerary_statuses=itinerary_statuses,
            trip_ready=trip_ready,
            proposal_sent_flag=proposal_sent_flag,
            mutation_reason="trip_updated",
            source_doctype="Trip",
            source_name=trip.name,
        )
        return

    if doc.doctype.lower() == "itinerary":
        itinerary = doc
        trip_name = getattr(itinerary, "trip", None)
        if not trip_name:
            # Itinerary not linked to a Trip yet; skip quietly
            return
        trip = frappe.get_doc("Trip", trip_name)
        contact = trip.customer
        if not contact:
            return
        story = ensure_story(contact)

        # refresh itineraries child table
        updated = False
        for row in story.get("itineraries") or []:
            if row.itinerary == itinerary.name:
                row.status = itinerary.status
                row.valid_from = itinerary.valid_from
                row.valid_to = itinerary.valid_to
                updated = True
                break
        if not updated:
            story.append(
                "itineraries",
                {
                    "itinerary": itinerary.name,
                    "status": itinerary.status,
                    "valid_from": itinerary.valid_from,
                    "valid_to": itinerary.valid_to,
                },
            )
        story.save(ignore_permissions=True)

        itins = _itineraries_for_trip(trip.name)
        has_itinerary = bool(itins)
        itinerary_statuses = [i["status"] for i in itins]

        intent = normalize.intent_from_trip(trip)
        trip_ready = rules.trip_ready_for_proposal(intent)
        facts_dict = normalize.story_facts_to_dict(story)
        proposal_sent_flag = rules.proposal_sent(facts_dict)

        choose_and_update_stage(
            story,
            has_contact=True,
            has_itinerary=has_itinerary,
            itinerary_statuses=itinerary_statuses,
            trip_ready=trip_ready,
            proposal_sent_flag=proposal_sent_flag,
            mutation_reason="itinerary_updated",
            source_doctype="Itinerary",
            source_name=itinerary.name,
        )
        return


def update_from_comm(doc, method: Optional[str] = None) -> None:
    comm = doc

    # Resolve contact: prefer Communication.reference_doctype/name when Contact; else use WhatsApp helper
    contact_name = None
    if getattr(comm, "reference_doctype", None) == "Contact" and getattr(comm, "reference_name", None):
        contact_name = comm.reference_name
    if not contact_name and hasattr(frappe.get_doc("Communication"), "get_or_create_contact_from_phone"):
        # unlikely path; using override class if available
        pass
    if not contact_name and getattr(comm, "phone_no", None):
        try:
            from frappe_whatsapp.overrides import WhatsAppCommunication

            contact_name = WhatsAppCommunication.get_or_create_contact_from_phone(comm.phone_no, auto_create=True)
        except Exception:
            contact_name = None

    if not contact_name:
        return

    story = ensure_story(contact_name)

    if str(comm.sent_or_received) == "Sent":
        itinerary_name, reason = extract_itinerary_ref_from_comm(comm)
        facts = normalize.story_facts_to_dict(story)
        already_sent = rules.proposal_sent(facts)
        if itinerary_name and not already_sent:
            mark_proposal_sent(contact_name, itinerary_name, comm.name, comm.creation)
        return

    if str(comm.sent_or_received) == "Received":
        trip_ready = False
        has_itinerary = False
        itinerary_statuses: List[str] = []

        if story.primary_trip:
            trip = frappe.get_doc("Trip", story.primary_trip)
            intent = normalize.intent_from_trip(trip)
            trip_ready = rules.trip_ready_for_proposal(intent)
            itins = _itineraries_for_trip(trip.name)
            has_itinerary = bool(itins)
            itinerary_statuses = [i["status"] for i in itins]

        facts_dict = normalize.story_facts_to_dict(story)
        proposal_sent_flag = rules.proposal_sent(facts_dict)

        choose_and_update_stage(
            story,
            has_contact=True,
            has_itinerary=has_itinerary,
            itinerary_statuses=itinerary_statuses,
            trip_ready=trip_ready,
            proposal_sent_flag=proposal_sent_flag,
            mutation_reason="inbound_message",
            source_doctype="Communication",
            source_name=comm.name,
            event_type="communication_created",
        )


