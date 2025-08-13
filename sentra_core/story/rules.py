from __future__ import annotations

from typing import Dict, List, Optional


STAGE_ORDER = {
    "Inquiry": 0,
    "Discovery": 1,
    "Proposal": 2,
    "Negotiation": 3,
    "Booking": 4,
    "Fulfillment": 5,
    "Post-trip": 6,
}


def trip_ready_for_proposal(intent: Dict) -> bool:
    destinations = intent.get("destinations") or []
    dates = intent.get("dates") or {}
    pax = intent.get("pax")

    has_destination = bool(destinations)

    start = dates.get("start")
    end = dates.get("end")
    flex = dates.get("flex")
    has_dates = bool(start and end) or (bool(flex) and str(flex) != "Exact dates")

    has_pax = bool(pax and int(pax) > 0)

    return has_destination and has_dates and has_pax


def proposal_sent(facts: Dict) -> bool:
    proposal = (facts or {}).get("proposal") or {}
    sent_at = proposal.get("sent_at")
    return bool(sent_at)


def choose_stage(
    current_stage: str,
    has_contact: bool,
    has_itinerary: bool,
    itinerary_statuses: List[str],
    trip_ready: bool,
    proposal_sent_flag: bool,
) -> str:
    # Ordered checks; first match wins
    target_stage: str

    if proposal_sent_flag:
        target_stage = "Negotiation"
    elif has_itinerary or trip_ready:
        target_stage = "Proposal"
    elif has_contact:
        target_stage = "Discovery"
    else:
        target_stage = "Inquiry"

    # Forward-only: never downgrade
    current_rank = STAGE_ORDER.get(current_stage or "Inquiry", 0)
    target_rank = STAGE_ORDER.get(target_stage, 0)
    if target_rank < current_rank:
        return current_stage or "Inquiry"
    return target_stage


