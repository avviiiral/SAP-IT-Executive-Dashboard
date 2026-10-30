"""Normalize source values to canonical ticket fields."""
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from django.utils import timezone

from tickets.models import TicketCategory, TicketChannel, TicketStatus


def clean_text(value):
    return "" if value is None else str(value).strip()


def parse_datetime(value, label):
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, date):
        parsed = datetime(value.year, value.month, value.day)
    else:
        text = clean_text(value)
        parsed = None
        for fmt in (None, "%d-%b-%Y", "%d-%m-%Y", "%d/%m/%Y", "%Y/%m/%d"):
            try:
                parsed = datetime.fromisoformat(text) if fmt is None else datetime.strptime(text, fmt)
                break
            except ValueError:
                continue
        if parsed is None:
            raise ValueError(f"{label} must be a valid date/time.")
    if timezone.is_naive(parsed):
        parsed = timezone.make_aware(parsed, timezone.get_current_timezone())
    return parsed


def parse_decimal(value, label):
    if value in (None, ""):
        return None
    try:
        result = Decimal(str(value).replace(",", "").strip())
    except (InvalidOperation, ValueError):
        raise ValueError(f"{label} must be numeric.") from None
    if result < 0:
        raise ValueError(f"{label} cannot be negative.")
    return result


def normalize_status(value):
    source = clean_text(value)
    key = source.casefold().replace("_", " ").replace("-", " ")
    mapping = {
        "resolved": TicketStatus.RESOLVED, "closed": TicketStatus.RESOLVED,
        "complete": TicketStatus.RESOLVED, "completed": TicketStatus.RESOLVED,
        "in progress": TicketStatus.IN_PROGRESS, "inprogress": TicketStatus.IN_PROGRESS,
        "work in progress": TicketStatus.IN_PROGRESS, "wip": TicketStatus.IN_PROGRESS,
        "on hold": TicketStatus.ON_HOLD, "hold": TicketStatus.ON_HOLD,
        "pending": TicketStatus.ON_HOLD, "open": TicketStatus.OPEN,
        "new": TicketStatus.OPEN, "assigned": TicketStatus.OPEN,
    }
    return mapping.get(key, TicketStatus.UNKNOWN), source


def normalize_category(value):
    source = clean_text(value)
    key = source.casefold()
    if key == "it":
        canonical = TicketCategory.IT
    elif key == "sap":
        canonical = TicketCategory.SAP
    elif key in {"", "unassigned", "unknown", "nan", "none"}:
        canonical = TicketCategory.UNASSIGNED
    else:
        canonical = TicketCategory.OTHER
    return canonical, source


def normalize_channel(value):
    source = clean_text(value)
    key = source.casefold().replace(" ", "")
    if key in {"webapp", "web", "portal"}:
        canonical = TicketChannel.WEBAPP
    elif key in {"email", "e-mail", "mail"}:
        canonical = TicketChannel.EMAIL
    elif not key:
        canonical = TicketChannel.UNKNOWN
    else:
        canonical = TicketChannel.OTHER
    return canonical, source
