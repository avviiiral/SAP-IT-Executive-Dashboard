"""Validate imported records against an explicit header mapping."""
from .normalization import (
    clean_text, normalize_category, normalize_channel, normalize_status,
    parse_datetime, parse_decimal,
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


def validate_field_map(field_map=None):
    mapping = dict(DEFAULT_FIELD_MAP)
    if field_map:
        if not isinstance(field_map, dict):
            raise ValueError("field_map must be a JSON object.")
        unknown = set(field_map) - ALLOWED_FIELDS
        if unknown:
            raise ValueError(f"Unsupported field(s): {', '.join(sorted(unknown))}")
        for field, header in field_map.items():
            if not isinstance(header, str) or not header.strip():
                raise ValueError(f"Header for {field} must be a non-empty string.")
            mapping[field] = header.strip()
    return mapping


def validate_row(source, mapping):
    incident = clean_text(source.get(mapping["incident_number"]))
    if not incident:
        raise ValueError("Incident number is required.")
    status, source_status = normalize_status(source.get(mapping["status"]))
    category, source_category = normalize_category(source.get(mapping["category"]))
    channel, source_channel = normalize_channel(source.get(mapping["channel"]))
    raw = {
        key: (value.isoformat() if hasattr(value, "isoformat") else value)
        for key, value in source.items() if key != "__row_number__"
    }
    return {
        "incident_number": incident,
        "title": clean_text(source.get(mapping["title"])),
        "status": status, "source_status": source_status,
        "category": category, "source_category": source_category,
        "subcategory": clean_text(source.get(mapping["subcategory"])),
        "plant_code": clean_text(source.get(mapping["plant_code"])),
        "channel": channel, "source_channel": source_channel,
        "assignee": clean_text(source.get(mapping["assignee"])),
        "created_at_source": parse_datetime(source.get(mapping["created_at_source"]), "Created date"),
        "resolved_at": parse_datetime(source.get(mapping["resolved_at"]), "Resolved date"),
        "resolution_days": parse_decimal(source.get(mapping["resolution_days"]), "Resolution days"),
        "due_at": parse_datetime(source.get(mapping["due_at"]), "Due date"),
        "raw_source_data": raw,
    }
