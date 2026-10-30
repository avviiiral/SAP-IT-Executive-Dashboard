"""Validate source rows using an explicit source-header mapping."""
from __future__ import annotations

from typing import Any

from .normalization import (
    clean_text,
    normalize_category,
    normalize_channel,
    normalize_status,
    parse_datetime,
    parse_decimal,
)


DEFAULT_FIELD_MAP = {
    "incident_number": "Incident Number",
    "title": "Title",
    "status": "Status",
    "category": "Category",
    "subcategory": "Subcategory",
    "plant_code": "Plant",
    "channel": "Channel",
    "assignee": "Assignee",
    "created_at_source": "Created Date",
    "resolved_at": "Resolved Date",
    "resolution_days": "Resolution Days",
    "due_at": "Due Date",
}

ALLOWED_FIELDS = set(DEFAULT_FIELD_MAP)
REQUIRED_FIELDS = {"incident_number"}


def validate_field_map(field_map: dict[str, str] | None) -> dict[str, str]:
    mapping = dict(DEFAULT_FIELD_MAP)
    if field_map:
        unknown = set(field_map) - ALLOWED_FIELDS
        if unknown:
            raise ValueError(f"Unsupported mapped field(s): {', '.join(sorted(unknown))}")
        for canonical, source_header in field_map.items():
            if not isinstance(source_header, str) or not source_header.strip():
                raise ValueError(f"Source header for {canonical} must be a non-empty string.")
            mapping[canonical] = source_header.strip()
    return mapping


def validate_row(source: dict[str, Any], mapping: dict[str, str]) -> dict[str, Any]:
    incident_number = clean_text(source.get(mapping["incident_number"]))
    if not incident_number:
        raise ValueError("Incident number is required.")

    status, source_status = normalize_status(source.get(mapping["status"]))
    category, source_category = normalize_category(source.get(mapping["category"]))
    channel, source_channel = normalize_channel(source.get(mapping["channel"]))

    return {
        "incident_number": incident_number,
        "title": clean_text(source.get(mapping["title"])),
        "status": status,
        "source_status": source_status,
        "category": category,
        "source_category": source_category,
        "subcategory": clean_text(source.get(mapping["subcategory"])),
        "plant_code": clean_text(source.get(mapping["plant_code"])),
        "channel": channel,
        "source_channel": source_channel,
        "assignee": clean_text(source.get(mapping["assignee"])),
        "created_at_source": parse_datetime(source.get(mapping["created_at_source"]), "Created date"),
        "resolved_at": parse_datetime(source.get(mapping["resolved_at"]), "Resolved date"),
        "resolution_days": parse_decimal(source.get(mapping["resolution_days"]), "Resolution days"),
        "due_at": parse_datetime(source.get(mapping["due_at"]), "Due date"),
        "raw_source_data": {
            key: (value.isoformat() if hasattr(value, "isoformat") else value)
            for key, value in source.items()
            if key != "__row_number__"
        },
    }
