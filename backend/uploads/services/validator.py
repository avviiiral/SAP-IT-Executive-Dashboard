"""Validate SAP service-desk exports against canonical ticket fields."""
from .normalization import (
    clean_text, normalize_category, normalize_channel, normalize_status,
    parse_datetime, parse_decimal,
)

# Exact column names from the SAP incident export supplied for this project.
# DUE is deliberately not mapped: the source column contains workflow text
# (for example "GO Live Done") as well as dates, so it is not a reliable due date.
DEFAULT_FIELD_MAP = {
    "incident_number": "INCNO",
    "title": "TITLE",
    "status": "STATUS",
    "category": "CTGRY",
    "subcategory": "SUB_CTGRY",
    "plant_code": "PCODE",
    "channel": "CHANL",
    "assignee": "ASN_TO",
    "created_at_source": "createdAt",
    "source_updated_at": "updatedAt",
    # updatedAt is the only available closure-time proxy in this export.
    # It is applied to resolved_at only for tickets whose source status is Resolved.
    "resolved_at": "updatedAt",
    "resolution_days": "Resolution Days",
    "due_at": "Due Date",
}
ALLOWED_FIELDS = set(DEFAULT_FIELD_MAP)

# Older generic exports remain supported when no explicit field_map is supplied.
DEFAULT_HEADER_ALIASES = {
    "incident_number": ("Incident Number", "Incident No", "Ticket ID"),
    "title": ("Title", "Short Description"),
    "status": ("Status",),
    "category": ("Category",),
    "subcategory": ("Subcategory", "Sub Category"),
    "plant_code": ("Plant", "Plant Code"),
    "channel": ("Channel",),
    "assignee": ("Assignee", "Assigned To"),
    "created_at_source": ("Created Date", "Created At"),
    "source_updated_at": ("Updated At", "Last Updated"),
    "resolved_at": ("Resolved Date", "Resolution Date"),
    "resolution_days": ("Resolution Days",),
    "due_at": ("Due Date",),
}


def resolve_field_map(field_map, headers, *, explicit=False):
    """Resolve legacy header aliases without overriding explicit user mappings."""
    mapping = dict(field_map)
    available = {header.casefold(): header for header in headers if header}
    for field, default_header in DEFAULT_FIELD_MAP.items():
        if explicit or default_header.casefold() in available:
            continue
        for alias in DEFAULT_HEADER_ALIASES.get(field, ()):
            if alias.casefold() in available:
                mapping[field] = available[alias.casefold()]
                break
    return mapping



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

    created_at = parse_datetime(
        source.get(mapping["created_at_source"]), "Created date"
    )
    source_updated_at = parse_datetime(
        source.get(mapping["source_updated_at"]), "Source updated date"
    )
    # The SAP export has no resolvedAt column. updatedAt is a documented proxy,
    # and must not be interpreted as a resolution timestamp for open tickets.
    resolved_at = (
        parse_datetime(source.get(mapping["resolved_at"]), "Resolution date")
        if status == "RESOLVED" else None
    )

    return {
        "incident_number": incident,
        "title": clean_text(source.get(mapping["title"])),
        "status": status, "source_status": source_status,
        "category": category, "source_category": source_category,
        "subcategory": clean_text(source.get(mapping["subcategory"])),
        "plant_code": clean_text(source.get(mapping["plant_code"])),
        "channel": channel, "source_channel": source_channel,
        "assignee": clean_text(source.get(mapping["assignee"])),
        "created_at_source": created_at,
        "source_updated_at": source_updated_at,
        "resolved_at": resolved_at,
        "resolution_days": parse_decimal(
            source.get(mapping["resolution_days"]), "Resolution days"
        ),
        # The supplied DUE field is intentionally not mapped by default.
        "due_at": parse_datetime(source.get(mapping["due_at"]), "Due date"),
        "raw_source_data": raw,
    }
