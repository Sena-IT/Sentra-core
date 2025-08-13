from __future__ import annotations

from typing import Any, Dict, List

import json


def intent_from_trip(trip_doc) -> Dict:
    destinations: List[str] = []
    for row in getattr(trip_doc, "destination_city", []) or []:
        # The child table stores a Link to Destination in fieldname 'destination'
        if getattr(row, "destination", None):
            destinations.append(row.destination)

    dates = {
        "start": getattr(trip_doc, "start_date", None),
        "end": getattr(trip_doc, "end_date", None),
        "flex": getattr(trip_doc, "flexible_days", None),
    }

    pax_value = getattr(trip_doc, "pax", None)
    if not pax_value:
        pax_value = len(getattr(trip_doc, "passenger_details", []) or [])

    return {
        "destinations": destinations,
        "dates": dates,
        "pax": pax_value,
    }


def story_facts_to_dict(story_doc) -> Dict[str, Any]:
    facts_map: Dict[str, Any] = {}

    rows = getattr(story_doc, "facts", []) or []
    # Latest occurrence wins via last_seen_at ordering
    sorted_rows = sorted(rows, key=lambda r: getattr(r, "last_seen_at", None) or getattr(r, "modified", None) or getattr(r, "creation", None))
    for row in sorted_rows:
        key_path = getattr(row, "key", "") or ""
        if not key_path:
            continue
        value_raw = getattr(row, "value", None)
        value: Any
        if isinstance(value_raw, str) and value_raw and (value_raw.strip().startswith("{") or value_raw.strip().startswith("[")):
            try:
                value = json.loads(value_raw)
            except Exception:
                value = value_raw
        else:
            value = value_raw

        # build nested dict by splitting on dots: e.g., proposal.sent_at
        parts = [p for p in key_path.split(".") if p]
        cursor = facts_map
        for i, part in enumerate(parts):
            if i == len(parts) - 1:
                cursor[part] = value
            else:
                if part not in cursor or not isinstance(cursor[part], dict):
                    cursor[part] = {}
                cursor = cursor[part]

    return facts_map


