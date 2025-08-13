from __future__ import annotations

from typing import Optional, Tuple

import re


ITINERARY_CODE_RE = re.compile(r"\bPCK-\d{4}-\d{4}\b", re.IGNORECASE)


def extract_itinerary_ref_from_comm(comm) -> tuple[Optional[str], Optional[str]]:
    # 1) Strong link via reference fields
    if getattr(comm, "reference_doctype", None) and str(comm.reference_doctype).lower() == "itinerary":
        ref_name = getattr(comm, "reference_name", None)
        if ref_name:
            return ref_name, "reference_link"

    # 2) Timeline links table
    for link in getattr(comm, "timeline_links", []) or []:
        if getattr(link, "link_doctype", None) and str(link.link_doctype).lower() == "itinerary":
            if getattr(link, "link_name", None):
                return link.link_name, "timeline_link"

    # 3) Parse content (HTML/text) and subject
    text_blobs = []
    if getattr(comm, "content", None):
        text_blobs.append(str(comm.content))
    if getattr(comm, "subject", None):
        text_blobs.append(str(comm.subject))

    for blob in text_blobs:
        # app path
        m = re.search(r"/app/itinerary/([A-Z0-9\-]+)", blob, re.IGNORECASE)
        if m:
            return m.group(1), "content_path"
        # code pattern
        m2 = ITINERARY_CODE_RE.search(blob)
        if m2:
            return m2.group(0), "code_pattern"

    return None, None


